# How operators could share meter data safely

**Why operators share:** each developer today starts from scratch because
metered data sits in private systems. Pooled data gives every operator better
forecasts than any one of them could build alone.

**What they give (minimum data only)**
- Monthly average kWh per customer for each site, in customer bands
  (household, small business, institution).
- Site start date, so growth after connection can be learned.
- Site location rounded to about 5 km, so no household can be identified.
- No names, meter IDs, phone numbers or individual bills. Ever.

**What they get back**
- A free benchmark report: how their sites compare with similar villages.
- Free forecasts for their next sites, from the pooled model.
- Credit as a contributor in the open model documentation.

**How it is kept safe**
1. A short data-use agreement: data is used only to train and test the model,
   never sold, and never shown at site level to competitors.
2. Only aggregated, rounded numbers leave the operator. Where an operator
   prefers, the model can be trained on the operator's own computer and only the
   trained model settings are shared (federated training).
3. A neutral host (for example an industry association) holds the pooled data
   and publishes only model results.
4. An operator can withdraw at any time and its data is removed at the next
   yearly retraining.

**First step (month 0 to 3):** sign 2 to 3 operators on a pilot agreement and
share one year of monthly data for 10 to 20 sites.
