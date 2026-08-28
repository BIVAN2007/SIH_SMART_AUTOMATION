function predictions = motionPredictor(tracks, horizon, dt)
% MOTIONPREDICTOR Predict short-term (horizon seconds) future positions
% for each track. Regular agents (cars) use constant-velocity/CTRV.
% Irregular agents (pedestrians, rickshaws, carts, cattle, two-wheelers)
% get a widening uncertainty cone to represent non-lane-based, erratic
% motion -- standing in for an LSTM/Seq2Seq multi-modal predictor
% (Deep Learning Toolbox) trained on logged RoadRunner trajectories.
%
% predictions(k): .id .type .steps(Nx2) .radius(Nx1)  [radius = 1-sigma
% uncertainty growing with time, used to inflate the occupancy risk map]

irregularTypes = {'pedestrian','auto_rickshaw','pushcart','cattle','two_wheeler'};

nSteps = round(horizon/dt);
predictions = struct('id',{},'type',{},'steps',{},'radius',{});

for k = 1:numel(tracks)
    tr = tracks(k);
    isIrregular = any(strcmp(tr.type, irregularTypes));

    steps = zeros(nSteps,2);
    radius = zeros(nSteps,1);
    p = tr.pos; v = tr.vel;

    baseSigma   = 0.25;                        % measurement/process base uncertainty (m)
    growthRate  = isIrregular * 0.55 + 0.12;    % irregular agents' cone widens much faster

    for s = 1:nSteps
        p = p + v*dt;
        if isIrregular
            % random-walk perturbation baked into the *predicted* mean too,
            % reflecting that irregular agents don't track a straight line
            p = p + 0.05*randn(1,2);
        end
        steps(s,:) = p;
        radius(s)  = baseSigma + growthRate * (s*dt);
    end

    predictions(end+1) = struct('id',tr.id,'type',tr.type,'steps',steps,'radius',radius); %#ok<AGROW>
end
end
