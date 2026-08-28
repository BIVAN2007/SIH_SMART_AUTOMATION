function [accel, steer] = purePursuitController(ego, traj, limits)
% PUREPURSUITCONTROLLER Convert a planned trajectory into steering
% (pure pursuit geometry) and acceleration (PID on target speed) commands.

lookahead = max(1.5, 0.6*ego.v);   % speed-scaled lookahead distance

% find lookahead point on trajectory
d = vecnorm(traj.xy - ego.pos, 2, 2);
idx = find(d >= lookahead, 1, 'first');
if isempty(idx), idx = size(traj.xy,1); end
targetPt = traj.xy(idx,:);
targetV  = traj.v(min(idx, numel(traj.v)));

% pure pursuit steering
dx = targetPt(1) - ego.pos(1); dy = targetPt(2) - ego.pos(2);
alpha = atan2(dy,dx) - ego.theta;
Ld = max(norm([dx dy]), 0.5);
steer = atan2(2*limits.wheelbase*sin(alpha), Ld);

% simple P controller on speed
kP = 0.8;
accel = kP*(targetV - ego.v);
end
