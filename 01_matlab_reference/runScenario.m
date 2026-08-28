function results = runScenario(scenarioName, opts)
% RUNSCENARIO Closed-loop simulation of the full pipeline on one scenario.
%
% opts (optional): .dt .simTime .planHorizon .replanEvery .verbose .seed
%
% results: struct with logged trajectory, per-step metrics, and summary
% metrics (collision, replanning latency stats, path smoothness, etc.)

if nargin < 2, opts = struct(); end
dt          = getOr(opts,'dt',0.1);
simTime     = getOr(opts,'simTime',22);
planHorizon = getOr(opts,'planHorizon',3.0);
replanEvery = getOr(opts,'replanEvery',0.3);   % seconds between replans (10Hz->~3Hz here for speed)
verbose     = getOr(opts,'verbose',true);
if isfield(opts,'seed'), rng(opts.seed); end

scn = generateScenario(scenarioName);

ego.pos   = scn.ego0(1:2);
ego.theta = scn.ego0(3);
ego.v     = scn.ego0(4);

limits.wheelbase = 2.7;
limits.maxV      = 25;
limits.maxAccel  = 2.5;
limits.maxDecel  = 6.0;
limits.maxSteer  = deg2rad(35);

sensorRanges.camera = 25; sensorRanges.lidar = 45; sensorRanges.max = 70;

agents = scn.agents;
tracks = struct('id',{},'type',{},'pos',{},'vel',{},'age',{},'missed',{});
dlState = [];

nSteps = round(simTime/dt);
log.pos = zeros(nSteps,2);
log.v   = zeros(nSteps,1);
log.mode = strings(nSteps,1);
log.minClearance = inf(nSteps,1);
log.replanLatency = [];
log.curvature = [];
log.collision = false;
log.goalReached = false;

currentTraj = [];
timeSinceReplan = inf;

for step = 1:nSteps
    t = step*dt;

    % --- ground-truth agent motion (RoadRunner Scenario actor logic stand-in) ---
    agents = stepAgents(agents, t, dt, scn.bounds);

    % --- perception: multi-sensor noisy detections ---
    dets = perceptionSim(agents, ego, sensorRanges);

    % --- sensor fusion / tracking ---
    tracks = sensorFusionTracker(tracks, dets, dt);

    % --- short-term motion prediction ---
    preds = motionPredictor(tracks, planHorizon, dt);

    % --- decision logic (Stateflow-equivalent) ---
    [mode, dlState] = decisionLogic(dlState, ego, tracks, scn.laneMarked, dt);

    % --- replanning (event-driven: fixed cadence here; in full system also
    %     triggered immediately when minClearRisk of current plan degrades) ---
    needReplan = isempty(currentTraj) || timeSinceReplan >= replanEvery || ...
                 (~isempty(currentTraj) && currentTraj.minClearRisk > 0.75);
    if needReplan
        [currentTraj, planInfo] = pathPlanner(ego, scn.goal, scn.staticObs, preds, scn.bounds, mode, dt, planHorizon);
        log.replanLatency(end+1) = planInfo.elapsedSec;
        timeSinceReplan = 0;
    else
        timeSinceReplan = timeSinceReplan + dt;
    end

    % --- control ---
    [accel, steer] = purePursuitController(ego, currentTraj, limits);

    % --- vehicle dynamics ---
    ego = vehicleModel(ego, accel, steer, dt, limits);

    % --- logging & safety metrics ---
    log.pos(step,:) = ego.pos;
    log.v(step) = ego.v;
    log.mode(step) = mode;

    minClear = inf;
    for k = 1:numel(agents)
        minClear = min(minClear, norm(agents(k).pos0 - ego.pos));
    end
    log.minClearance(step) = minClear;
    if minClear < 0.6
        log.collision = true;
    end

    if norm(ego.pos - scn.goal) < 3.0
        log.goalReached = true;
        log.pos = log.pos(1:step,:); log.v = log.v(1:step);
        log.mode = log.mode(1:step); log.minClearance = log.minClearance(1:step);
        break;
    end
end

% --- path smoothness metric: mean squared curvature of the driven path ---
P = log.pos;
if size(P,1) > 3
    dP  = diff(P);
    ang = atan2(dP(2:end,2),dP(2:end,1)) - atan2(dP(1:end-1,2),dP(1:end-1,1));
    ang = mod(ang+pi,2*pi)-pi;
    ds  = vecnorm(dP(1:end-1,:),2,2) + 1e-6;
    curv = ang ./ ds;
    smoothness = mean(curv.^2);
else
    smoothness = NaN;
end

results.scenario         = scn.name;
results.log              = log;
results.collision        = log.collision;
results.goalReached      = log.goalReached;
results.minClearanceOverall = min(log.minClearance);
results.meanReplanLatencyMs = 1000*mean(log.replanLatency);
results.p95ReplanLatencyMs  = 1000*simplePrctile(log.replanLatency,95);
results.pathSmoothness      = smoothness;
results.simSteps            = size(P,1);

if verbose
    fprintf('[%s] goalReached=%d collision=%d minClear=%.2fm meanReplan=%.1fms p95=%.1fms smoothness=%.4f\n', ...
        results.scenario, results.goalReached, results.collision, results.minClearanceOverall, ...
        results.meanReplanLatencyMs, results.p95ReplanLatencyMs, results.pathSmoothness);
end
end

function v = getOr(s,f,d)
if isfield(s,f), v = s.(f); else, v = d; end
end

function p = simplePrctile(x, pct)
% Minimal percentile implementation (avoids Statistics & ML Toolbox dependency)
x = sort(x(:));
n = numel(x);
if n == 0, p = NaN; return; end
if n == 1, p = x(1); return; end
r = (pct/100)*(n-1) + 1;
lo = floor(r); hi = ceil(r);
if lo == hi, p = x(lo); else, p = x(lo) + (r-lo)*(x(hi)-x(lo)); end
end
