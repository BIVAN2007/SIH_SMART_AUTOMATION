function [bestTraj, planInfo] = pathPlanner(ego, goal, staticObs, predictions, bounds, mode, dt, horizon)
% PATHPLANNER Sampling-based local lattice / DWA-style planner.
% Generates a fan of candidate (curvature, speed) trajectories from the
% ego's current state, scores each against a TIME-INDEXED occupancy risk
% map (so a candidate is only penalized for where an agent is PREDICTED
% to be at the time the ego would actually reach that point -- this is
% the core "predict-then-plan" trick), plus smoothness/progress cost.
%
% This stands in for plannerHybridAStar / plannerRRTStar (global) combined
% with a Frenet-lattice or DWA local planner (Navigation Toolbox), with
% mode ('normal'|'crawl'|'yield'|'emergency') coming from the Stateflow
% decision-logic layer to reweight the cost function / speed envelope.
%
% Returns bestTraj: struct with .xy (Nx2), .v (Nx1), .cost, .minClearRisk
% planInfo: struct with .nCandidates .elapsedSec (for replanning-latency metric)

tPlanStart = tic;

res = 1.0;                    % risk-grid resolution (m)
nSteps = round(horizon/dt);

% --- speed envelope depends on decision-logic mode ---
switch mode
    case 'emergency'
        vCandidates = max(ego.v - 4, 0):1:max(ego.v,1);   % hard braking fan
    case 'yield'
        vCandidates = linspace(0, max(ego.v*0.5,1), 3);
    case 'crawl'
        vCandidates = linspace(1, min(ego.v+1,4), 3);
    otherwise % 'normal'
        vCandidates = linspace(max(ego.v-2,0), ego.v+2, 4);
end
curvCandidates = linspace(-0.12, 0.12, 9);   % 1/m, steering-arc fan

% --- precompute the time-indexed risk maps ONCE per replan (they depend
% only on predicted agent positions at step s, not on the candidate being
% scored) -- avoids O(candidates x steps) redundant grid rebuilds ---
riskMaps = cell(nSteps,1);
for s = 1:nSteps
    riskMaps{s} = occupancyRiskMap(bounds, res, staticObs, predictions, s);
end

bestTraj = []; bestCost = inf; nCand = 0;

for v = vCandidates
    for c = curvCandidates
        nCand = nCand + 1;
        [xy, thetas] = simulateArc(ego, v, c, dt, nSteps);

        % out-of-bounds check
        if any(xy(:,1) < bounds(1)) || any(xy(:,1) > bounds(2)) || ...
           any(xy(:,2) < bounds(3)) || any(xy(:,2) > bounds(4))
            continue;
        end

        % --- collision/risk cost: sample the risk map AT EACH STEP'S
        % OWN future time index (this is the real-time-replanning core) ---
        riskCost = 0; maxRiskOnPath = 0;
        for s = 1:nSteps
            map = riskMaps{s};
            gx = round((xy(s,1)-bounds(1))/res)+1;
            gy = round((xy(s,2)-bounds(3))/res)+1;
            gx = min(max(gx,1), numel(map.xs));
            gy = min(max(gy,1), numel(map.ys));
            r = map.risk(gy,gx);
            riskCost = riskCost + r^2 * (nSteps-s+1)/nSteps;  % near-term risk weighted higher
            maxRiskOnPath = max(maxRiskOnPath, r);
        end
        if maxRiskOnPath > 0.9
            continue;   % hard reject: predicted collision
        end

        % --- smoothness cost: curvature magnitude + curvature change ---
        smoothCost = abs(c)*3;

        % --- progress cost: distance remaining to goal after this arc ---
        progressCost = norm(xy(end,:) - goal);

        % --- mode-based speed-shaping (reward matching envelope's intent) ---
        speedCost = 0.1*abs(v - ego.v);

        totalCost = 8*riskCost + 1.5*smoothCost + 1.0*progressCost + speedCost;

        if totalCost < bestCost
            bestCost = totalCost;
            bestTraj.xy = xy;
            bestTraj.theta = thetas;
            bestTraj.v = v*ones(nSteps,1);
            bestTraj.cost = totalCost;
            bestTraj.minClearRisk = maxRiskOnPath;
        end
    end
end

% fallback: if every candidate hard-rejected (surrounded), emergency stop in place
if isempty(bestTraj)
    xy = repmat(ego.pos, nSteps, 1);
    bestTraj.xy = xy; bestTraj.theta = ego.theta*ones(nSteps,1);
    bestTraj.v = zeros(nSteps,1); bestTraj.cost = inf; bestTraj.minClearRisk = 1;
end

planInfo.nCandidates = nCand;
planInfo.elapsedSec  = toc(tPlanStart);
end

function [xy, thetas] = simulateArc(ego, v, curvature, dt, nSteps)
% Simple kinematic bicycle-model rollout for one candidate (v, curvature)
xy = zeros(nSteps,2); thetas = zeros(nSteps,1);
x = ego.pos(1); y = ego.pos(2); th = ego.theta;
for s = 1:nSteps
    th = th + v*curvature*dt;
    x  = x + v*cos(th)*dt;
    y  = y + v*sin(th)*dt;
    xy(s,:) = [x y]; thetas(s) = th;
end
end
