function map = occupancyRiskMap(bounds, res, staticObs, predictions, tStepIdx)
% OCCUPANCYRISKMAP Build a 2D risk grid at a given future timestep index.
% Cell value in [0,1]: probability-like collision risk (Gaussian blobs
% around predicted agent positions, inflated by uncertainty radius, plus
% hard-occupied static obstacles).

xs = bounds(1):res:bounds(2);
ys = bounds(3):res:bounds(4);
[X,Y] = meshgrid(xs,ys);
risk = zeros(size(X));

% static obstacles: hard risk = 1 within radius, soft falloff outside
for i = 1:size(staticObs,1)
    ox = staticObs(i,1); oy = staticObs(i,2); r = staticObs(i,3);
    d = sqrt((X-ox).^2 + (Y-oy).^2);
    risk = max(risk, exp(-max(d-r,0).^2 / (2*(0.6)^2)) .* (d < r+2.5));
    risk(d <= r) = 1;
end

% dynamic agents at this future step: Gaussian risk centered on predicted pos
for k = 1:numel(predictions)
    pr = predictions(k);
    if tStepIdx > size(pr.steps,1), continue; end
    cx = pr.steps(tStepIdx,1); cy = pr.steps(tStepIdx,2);
    sigma = max(pr.radius(tStepIdx), 0.3);
    d2 = (X-cx).^2 + (Y-cy).^2;
    riskAgent = exp(-d2 / (2*sigma^2));
    risk = max(risk, riskAgent);
end

map.xs = xs; map.ys = ys; map.risk = risk; map.res = res; map.bounds = bounds;
end
