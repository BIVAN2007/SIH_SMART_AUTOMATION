function visualizeScenario(scenarioName, opts)
% VISUALIZESCENARIO Re-run one scenario step-by-step with live animation
% of ego (blue), agents (colored by type), static obstacles, and planned
% trajectory. Use this to screen-record the demo video deliverable.

if nargin < 2, opts = struct(); end
dt = 0.1; simTime = getOr(opts,'simTime',22); planHorizon = 3.0; replanEvery = 0.3;
if isfield(opts,'seed'), rng(opts.seed); end

scn = generateScenario(scenarioName);
ego.pos = scn.ego0(1:2); ego.theta = scn.ego0(3); ego.v = scn.ego0(4);
limits.wheelbase = 2.7; limits.maxV = 25; limits.maxAccel = 2.5; limits.maxDecel = 6.0; limits.maxSteer = deg2rad(35);
sensorRanges.camera = 25; sensorRanges.lidar = 45; sensorRanges.max = 70;

agents = scn.agents;
tracks = struct('id',{},'type',{},'pos',{},'vel',{},'age',{},'missed',{});
dlState = []; currentTraj = []; timeSinceReplan = inf;

figure('Name',['Live: ' scn.name],'Position',[100 100 1000 500]);
colors = containers.Map({'car','auto_rickshaw','pedestrian','pushcart','cattle','two_wheeler'}, ...
    {[0 0.4 1],[1 0.5 0],[1 0 0],[0.6 0.3 0],[0.3 0.7 0.3],[0.8 0 0.8]});

nSteps = round(simTime/dt);
for step = 1:nSteps
    t = step*dt;
    agents = stepAgents(agents, t, dt, scn.bounds);
    dets = perceptionSim(agents, ego, sensorRanges);
    tracks = sensorFusionTracker(tracks, dets, dt);
    preds = motionPredictor(tracks, planHorizon, dt);
    [mode, dlState] = decisionLogic(dlState, ego, tracks, scn.laneMarked, dt);

    if isempty(currentTraj) || timeSinceReplan >= replanEvery
        [currentTraj, ~] = pathPlanner(ego, scn.goal, scn.staticObs, preds, scn.bounds, mode, dt, planHorizon);
        timeSinceReplan = 0;
    else
        timeSinceReplan = timeSinceReplan + dt;
    end

    [accel, steer] = purePursuitController(ego, currentTraj, limits);
    ego = vehicleModel(ego, accel, steer, dt, limits);

    if mod(step,2)==0   % render every other step for speed
        clf; hold on; axis equal; grid on;
        xlim(scn.bounds(1:2)); ylim(scn.bounds(3:4));
        title(sprintf('%s | t=%.1fs | mode=%s', scn.name, t, mode), 'Interpreter','none');

        % static obstacles (drawn manually to avoid Image Processing Toolbox dependency)
        thc = linspace(0,2*pi,30);
        for i = 1:size(scn.staticObs,1)
            cx = scn.staticObs(i,1); cy = scn.staticObs(i,2); r = scn.staticObs(i,3);
            fill(cx+r*cos(thc), cy+r*sin(thc), [0.3 0.3 0.3], 'FaceAlpha',0.5, 'EdgeColor','k');
        end
        % planned trajectory
        if ~isempty(currentTraj)
            plot(currentTraj.xy(:,1), currentTraj.xy(:,2), 'g--','LineWidth',1.5);
        end
        % driven path so far
        plot(ego.pos(1), ego.pos(2), 'bs', 'MarkerFaceColor','b','MarkerSize',10);
        % agents
        for k = 1:numel(agents)
            c = [0.5 0.5 0.5];
            if isKey(colors, agents(k).type), c = colors(agents(k).type); end
            plot(agents(k).pos0(1), agents(k).pos0(2), 'o', 'MarkerFaceColor',c,'MarkerEdgeColor','k','MarkerSize',8);
            text(agents(k).pos0(1)+0.5, agents(k).pos0(2)+0.5, agents(k).type, 'FontSize',7,'Interpreter','none');
        end
        plot(scn.goal(1), scn.goal(2), 'kp', 'MarkerFaceColor','y','MarkerSize',14);
        drawnow;
    end

    if norm(ego.pos - scn.goal) < 3.0, break; end
end
end

function v = getOr(s,f,d)
if isfield(s,f), v = s.(f); else, v = d; end
end
