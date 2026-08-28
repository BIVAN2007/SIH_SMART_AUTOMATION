function agents = stepAgents(agents, t, dt, bounds)
% STEPAGENTS Advance ground-truth agent positions one timestep according
% to their scripted / stochastic behavior model. This stands in for
% RoadRunner Scenario actor logic when running outside RoadRunner.

for i = 1:numel(agents)
    a = agents(i);

    switch a.behavior
        case 'straight'
            % constant velocity

        case 'weave'
            % irregular, non-lane-based lateral drift (rickshaws/two-wheelers/pushcarts)
            a.vel0(2) = a.vel0(2) + 0.6*randn()*dt*5;
            a.vel0(2) = max(min(a.vel0(2), 3), -3);

        case 'randomWalk'
            % pedestrians: small random accelerations, can reverse direction
            a.vel0 = a.vel0 + 0.4*randn(1,2)*dt*5;
            spd = norm(a.vel0);
            if spd > 1.6, a.vel0 = a.vel0/spd*1.6; end

        case 'suddenCross'
            if t < a.triggerT
                a.vel0 = [0 0];         % idle at roadside until triggered
            else
                % bolt across the road at speed once triggered
                a.vel0 = [0 sign(a.vel0(2)+eps)*3.2];
            end

        case 'mergeSlow'
            if t < a.triggerT
                a.vel0 = [a.vel0(1) 0];  % holding on shoulder
            else
                a.vel0 = [a.vel0(1) -1.0]; % slowly merges toward main carriageway
            end
    end

    a.pos0 = a.pos0 + a.vel0*dt;

    % keep within scenario bounds (simple clamp/reflect)
    if a.pos0(1) < bounds(1) || a.pos0(1) > bounds(2), a.vel0(1) = -a.vel0(1); end
    if a.pos0(2) < bounds(3) || a.pos0(2) > bounds(4), a.vel0(2) = -a.vel0(2); end

    agents(i) = a;
end
end
