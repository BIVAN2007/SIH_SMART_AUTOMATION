% RUNALLSCENARIOS Run all 5 required Indian-road scenarios (with repeated
% trials for statistical robustness), aggregate metrics, and plot results.
% This is the script to run for the "Part 3: results" deliverable.

clear; clc; close all;
addpath(pwd);

scenarios = {'village_road','urban_intersection','highway_merge','market_area','cattle_crossing'};
nTrials = 5;   % Monte Carlo repeats per scenario (increase for final report)

allResults = {};
summaryRows = [];

for si = 1:numel(scenarios)
    name = scenarios{si};
    fprintf('\n=== Scenario: %s ===\n', name);
    trialResults = cell(1,nTrials);
    for trial = 1:nTrials
        opts = struct('seed', trial*100+si, 'verbose', true);
        r = runScenario(name, opts);
        trialResults{trial} = r;
    end
    allResults{si} = trialResults; %#ok<AGROW>

    completion = mean(cellfun(@(r) r.goalReached && ~r.collision, trialResults))*100;
    collisionRate = mean(cellfun(@(r) r.collision, trialResults))*100;
    meanLatency = mean(cellfun(@(r) r.meanReplanLatencyMs, trialResults));
    p95Latency  = mean(cellfun(@(r) r.p95ReplanLatencyMs, trialResults));
    smooth = mean(cellfun(@(r) r.pathSmoothness, trialResults),'omitnan');
    minClear = mean(cellfun(@(r) r.minClearanceOverall, trialResults));

    summaryRows = [summaryRows; {name, completion, collisionRate, meanLatency, p95Latency, smooth, minClear}]; %#ok<AGROW>
end

metricsTable = cell2table(summaryRows, 'VariableNames', ...
    {'Scenario','CompletionRatePct','CollisionRatePct','MeanReplanLatencyMs', ...
     'P95ReplanLatencyMs','PathSmoothness','MeanMinClearance_m'});

disp(' ');
disp('=== Aggregate Metrics Summary ===');
disp(metricsTable);

save('adas_results.mat','allResults','metricsTable');
writetable(metricsTable,'adas_metrics_summary.csv');

%% Plots for the report
figure('Name','Completion & Collision Rate','Position',[100 100 700 400]);
bar(categorical(metricsTable.Scenario), [metricsTable.CompletionRatePct, metricsTable.CollisionRatePct]);
legend('Completion Rate (%)','Collision Rate (%)'); ylabel('%');
title('Scenario Completion vs Collision Rate'); grid on;

figure('Name','Replanning Latency','Position',[100 550 700 400]);
bar(categorical(metricsTable.Scenario), [metricsTable.MeanReplanLatencyMs, metricsTable.P95ReplanLatencyMs]);
legend('Mean latency (ms)','P95 latency (ms)'); ylabel('ms');
title('Replanning Latency by Scenario'); grid on;

figure('Name','Path Smoothness & Clearance','Position',[850 100 700 400]);
yyaxis left; bar(categorical(metricsTable.Scenario), metricsTable.PathSmoothness); ylabel('Mean curvature^2');
yyaxis right; plot(categorical(metricsTable.Scenario), metricsTable.MeanMinClearance_m,'-o','LineWidth',2);
ylabel('Min clearance (m)');
title('Path Smoothness & Minimum Clearance'); grid on;

% Example top-down trajectory plot for one trial per scenario
figure('Name','Sample Trajectories','Position',[850 550 900 500]);
for si = 1:numel(scenarios)
    subplot(2,3,si);
    r = allResults{si}{1};
    plot(r.log.pos(:,1), r.log.pos(:,2), 'b-', 'LineWidth',1.5); hold on;
    title(r.scenario, 'Interpreter','none'); xlabel('x (m)'); ylabel('y (m)'); axis equal; grid on;
end
sgtitle('Sample Ego Trajectories (Trial 1) per Scenario');

fprintf('\nSaved: adas_results.mat, adas_metrics_summary.csv, and figures generated.\n');
