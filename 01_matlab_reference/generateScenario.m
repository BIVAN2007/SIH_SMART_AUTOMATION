function scn = generateScenario(name)
% GENERATESCENARIO Build one of the 5 required Indian-road test scenarios.
%
% scn fields:
%   name          : string
%   bounds        : [xmin xmax ymin ymax]  (meters)
%   goal          : [x y]
%   ego0          : [x y theta v]
%   laneMarked    : true/false  (drives Stateflow behavior mode)
%   staticObs     : Nx3 [x y radius]
%   agents        : struct array, each with:
%       type      : 'car'|'auto_rickshaw'|'pedestrian'|'pushcart'|'cattle'|'two_wheeler'
%       pos0      : [x y]
%       vel0      : [vx vy]
%       behavior  : 'straight'|'weave'|'randomWalk'|'suddenCross'|'mergeSlow'
%       triggerT  : time (s) at which a scripted event (e.g. cattle enters) fires
%       irregular : true/false -> widens prediction uncertainty cone
%
% dt / horizon handled by caller.

switch lower(name)

    case 'village_road'   % Scenario 1: unmarked village road
        scn.name = 'Village Road (Unmarked)';
        scn.bounds = [0 120 -10 10];
        scn.laneMarked = false;
        scn.ego0 = [5 0 0 6];         % v in m/s ~ 21 km/h, rural crawl
        scn.goal = [110 2];
        scn.staticObs = [45 -3 1.2; 70 4 1.0];   % pothole/debris markers
        scn.agents = struct('type',{},'pos0',{},'vel0',{},'behavior',{},'triggerT',{},'irregular',{});
        scn.agents(end+1) = agentDef('pedestrian', [40 5],  [-0.3 -1.0], 'weave', 0, true);
        scn.agents(end+1) = agentDef('two_wheeler',[20 -6], [3.5 0.6],  'weave', 0, true);
        scn.agents(end+1) = agentDef('pushcart',   [60 3],  [0.4 -0.2], 'randomWalk', 0, true);

    case 'urban_intersection'   % Scenario 2: busy unsignaled intersection
        scn.name = 'Urban Unsignaled Intersection';
        scn.bounds = [-10 60 -30 30];
        scn.laneMarked = true;
        scn.ego0 = [-5 0 0 8];
        scn.goal = [55 0];
        scn.staticObs = zeros(0,3);
        scn.agents = struct('type',{},'pos0',{},'vel0',{},'behavior',{},'triggerT',{},'irregular',{});
        scn.agents(end+1) = agentDef('auto_rickshaw',[25 -20],[0.5 4.2], 'weave', 0, true);
        scn.agents(end+1) = agentDef('car',          [25  22],[0.2 -4.0],'straight', 0, false);
        scn.agents(end+1) = agentDef('two_wheeler',  [10 -15],[2.5 3.0], 'weave', 0, true);
        scn.agents(end+1) = agentDef('pedestrian',   [25 -3], [0.0 1.2], 'randomWalk', 0, true);

    case 'highway_merge'   % Scenario 3: highway merge with slow-moving vehicles
        scn.name = 'Highway Merge (Slow Mergers)';
        scn.bounds = [0 200 -8 8];
        scn.laneMarked = true;
        scn.ego0 = [5 -3 0 22];        % ~80 km/h
        scn.goal = [190 -3];
        scn.staticObs = zeros(0,3);
        scn.agents = struct('type',{},'pos0',{},'vel0',{},'behavior',{},'triggerT',{},'irregular',{});
        scn.agents(end+1) = agentDef('car',[60 -3],[18 0],'straight',0,false);
        scn.agents(end+1) = agentDef('auto_rickshaw',[80 6],[6 -1.2],'mergeSlow',2.0,true);   % merging in slowly
        scn.agents(end+1) = agentDef('car',[130 -3],[14 0],'straight',0,false);               % slow truck-like

    case 'market_area'   % Scenario 4: dense market, mixed traffic, crawl speed
        scn.name = 'Dense Market Area (Mixed Traffic)';
        scn.bounds = [0 80 -8 8];
        scn.laneMarked = false;
        scn.ego0 = [3 0 0 3];          % crawl speed ~11 km/h
        scn.goal = [75 1];
        scn.staticObs = [30 -2 1.0; 50 3 0.8; 55 -1 0.9];  % stalls/parked carts
        scn.agents = struct('type',{},'pos0',{},'vel0',{},'behavior',{},'triggerT',{},'irregular',{});
        scn.agents(end+1) = agentDef('pedestrian', [15  2],[0.2 -0.9],'randomWalk',0,true);
        scn.agents(end+1) = agentDef('pedestrian', [35 -3],[0.1  0.8],'randomWalk',0,true);
        scn.agents(end+1) = agentDef('pushcart',   [45  1],[-0.3 0.1],'weave',0,true);
        scn.agents(end+1) = agentDef('two_wheeler',[10 -4],[2.0 0.9],'weave',0,true);
        scn.agents(end+1) = agentDef('auto_rickshaw',[60 4],[-1.0 -0.5],'weave',0,true);

    case 'cattle_crossing'   % Scenario 5: sudden cattle crossing
        scn.name = 'Sudden Cattle Crossing';
        scn.bounds = [0 100 -10 10];
        scn.laneMarked = false;
        scn.ego0 = [5 0 0 12];
        scn.goal = [95 0];
        scn.staticObs = zeros(0,3);
        scn.agents = struct('type',{},'pos0',{},'vel0',{},'behavior',{},'triggerT',{},'irregular',{});
        % cattle idle off-road until triggerT, then bolts across -> worst-case reaction test
        scn.agents(end+1) = agentDef('cattle',[50 -9],[0 3.2],'suddenCross', 2.5, true);
        scn.agents(end+1) = agentDef('cattle',[53 -9],[0 3.0],'suddenCross', 2.7, true);

    otherwise
        error('Unknown scenario "%s". Use: village_road | urban_intersection | highway_merge | market_area | cattle_crossing', name);
end
end

function a = agentDef(type,pos0,vel0,behavior,triggerT,irregular)
a.type = type; a.pos0 = pos0; a.vel0 = vel0;
a.behavior = behavior; a.triggerT = triggerT; a.irregular = irregular;
end
