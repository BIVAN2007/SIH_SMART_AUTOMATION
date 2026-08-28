function detections = perceptionSim(agents, ego, sensorRanges)
% PERCEPTIONSIM Simulate fused camera+LiDAR+radar detections with
% realistic noise/dropout, standing in for:
%   - Automated Driving Toolbox camera/LiDAR/radar sensor models
%   - a trained Deep-Learning-Toolbox object detector (class + bbox)
%
% detections(i): .type .pos .vel .classConf .rangeSensor

detections = struct('type',{},'pos',{},'vel',{},'classConf',{},'rangeSensor',{});

for i = 1:numel(agents)
    a = agents(i);
    d = norm(a.pos0 - ego.pos);
    if d > sensorRanges.max, continue; end   % out of all sensor range

    % sensor selection by range/type (camera: classification+short/mid range,
    % LiDAR: precise position mid-range, radar: velocity + long range)
    if d < sensorRanges.camera
        posNoise = 0.15; velNoise = 0.3; conf = 0.92; src = 'camera+lidar';
    elseif d < sensorRanges.lidar
        posNoise = 0.30; velNoise = 0.5; conf = 0.80; src = 'lidar';
    else
        posNoise = 0.60; velNoise = 0.4; conf = 0.55; src = 'radar';  % coarse pos, good velocity
    end

    % random missed-detection probability (occlusion in dense market/intersection)
    pMiss = 0.03 + 0.05*(strcmp(a.type,'pedestrian') || strcmp(a.type,'pushcart'));
    if rand() < pMiss, continue; end

    det.type        = a.type;
    det.pos          = a.pos0 + posNoise*randn(1,2);
    det.vel          = a.vel0 + velNoise*randn(1,2);
    det.classConf    = min(1, max(0.3, conf + 0.05*randn()));
    det.rangeSensor  = src;
    detections(end+1) = det; %#ok<AGROW>
end
end
