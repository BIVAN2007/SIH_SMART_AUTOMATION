function [mode, state] = decisionLogic(state, ego, tracks, laneMarked, dt)
% DECISIONLOGIC MATLAB state machine equivalent of a Stateflow chart with
% states: LaneFollow / UnmarkedRoadFollow / Yield / Crawl / EmergencyStop.
% In the actual Simulink model this block is a Stateflow chart driven by
% the same signals (minTTC, nearestAgentDist, laneMarked, agentDensity);
% implemented here in code for a pure-MATLAB runnable pipeline.
%
% state: persists across calls ('mode','timeInState')
% mode : string returned to the planner to reweight cost/speed envelope

if isempty(state)
    state = struct('mode','LaneFollow','timeInState',0);
end

% --- compute decision features from current tracks ---
minTTC = inf; nearestDist = inf; density = numel(tracks);
for k = 1:numel(tracks)
    rel = tracks(k).pos - ego.pos;
    d = norm(rel);
    nearestDist = min(nearestDist, d);
    closingSpeed = -dot(tracks(k).vel - [ego.v*cos(ego.theta) ego.v*sin(ego.theta)], rel/max(d,1e-6));
    if closingSpeed > 0.3
        ttc = d / closingSpeed;
        minTTC = min(minTTC, ttc);
    end
end

prevMode = state.mode;

% --- transition logic ---
if minTTC < 1.2 || nearestDist < 2.0
    newMode = 'EmergencyStop';
elseif minTTC < 3.0 || nearestDist < 4.5
    newMode = 'Yield';
elseif density >= 4 || ~laneMarked && nearestDist < 8
    newMode = 'Crawl';
elseif ~laneMarked
    newMode = 'UnmarkedRoadFollow';
else
    newMode = 'LaneFollow';
end

if strcmp(newMode, prevMode)
    state.timeInState = state.timeInState + dt;
else
    state.timeInState = 0;
end
state.mode = newMode;

% map Stateflow-style state name -> planner mode keyword
switch newMode
    case 'EmergencyStop', mode = 'emergency';
    case 'Yield',          mode = 'yield';
    case 'Crawl',          mode = 'crawl';
    otherwise,             mode = 'normal';   % LaneFollow / UnmarkedRoadFollow
end
end
