# identify-nrusage-dashboards
New Relic will be deprecating the usage event types NrUsage and NrDailyUsage and replacing with NrConsumption and NrMTDConsumption.

When run with a valid New Relic user API key, this script will identify all dashboards with widgets that execute queries against NrUsage and NrDailyUsage so that customers may more easily manage the transition to the new event types.
