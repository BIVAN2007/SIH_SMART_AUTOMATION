function tracks = sensorFusionTracker(tracks, detections, dt)
% SENSORFUSIONTRACKER Nearest-neighbor data association + exponential
% smoothing filter per track. Stands in for Sensor Fusion & Automated
% Driving Toolbox's trackerJPDA / trackerGNN for hackathon-scale sim.
%
% tracks(k): .id .type .pos .vel .age .missed

persistent nextID
if isempty(nextID), nextID = 1; end

assigned = false(1,numel(detections));

% --- predict existing tracks forward ---
for k = 1:numel(tracks)
    tracks(k).pos = tracks(k).pos + tracks(k).vel*dt;
    tracks(k).age = tracks(k).age + 1;
    tracks(k).missed = tracks(k).missed + 1;
end

% --- associate detections to nearest track of same type within gate ---
gate = 3.0; % meters
for k = 1:numel(tracks)
    bestJ = -1; bestD = gate;
    for j = 1:numel(detections)
        if assigned(j) || ~strcmp(detections(j).type, tracks(k).type), continue; end
        d = norm(detections(j).pos - tracks(k).pos);
        if d < bestD, bestD = d; bestJ = j; end
    end
    if bestJ > 0
        alpha = 0.6; % filter gain (stand-in for EKF update)
        tracks(k).pos    = (1-alpha)*tracks(k).pos + alpha*detections(bestJ).pos;
        tracks(k).vel    = (1-alpha)*tracks(k).vel + alpha*detections(bestJ).vel;
        tracks(k).missed = 0;
        assigned(bestJ)  = true;
    end
end

% --- spawn new tracks for unassigned detections ---
for j = 1:numel(detections)
    if assigned(j), continue; end
    t.id = nextID; nextID = nextID + 1;
    t.type = detections(j).type;
    t.pos  = detections(j).pos;
    t.vel  = detections(j).vel;
    t.age  = 1; t.missed = 0;
    tracks(end+1) = t; %#ok<AGROW>
end

% --- prune stale tracks ---
if ~isempty(tracks)
    tracks = tracks([tracks.missed] < 5);
end
end
