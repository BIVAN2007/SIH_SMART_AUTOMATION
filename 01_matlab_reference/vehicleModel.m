function ego = vehicleModel(ego, accel, steerRate, dt, limits)
% VEHICLEMODEL Kinematic bicycle model propagation for the ego vehicle.
% In the real Simulink model this block is replaced by Vehicle Dynamics
% Blockset's dynamic single-track model / a Simulink bicycle subsystem.
%
% ego: .pos [x y] .theta .v
% limits: .maxV .maxAccel .maxDecel .maxSteer .wheelbase

L = limits.wheelbase;

accel = min(max(accel, -limits.maxDecel), limits.maxAccel);
ego.v = min(max(ego.v + accel*dt, 0), limits.maxV);

steer = min(max(steerRate, -limits.maxSteer), limits.maxSteer);
ego.theta = ego.theta + (ego.v/L)*tan(steer)*dt;

ego.pos(1) = ego.pos(1) + ego.v*cos(ego.theta)*dt;
ego.pos(2) = ego.pos(2) + ego.v*sin(ego.theta)*dt;
end
