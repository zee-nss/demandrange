# Solution outline: one-page summary source (aligned to the coach's questions)

Fill the [brackets]. Keep each answer to two or three sentences. Never present simulated results as real.

| Prompt | Answer |
|---|---|
| Team | Zeenah (AI and software lead) and Nancy Wangare ([role]) |
| Brief, track, setting | 03 Predict mini-grid demand before building. Track 2, Digital Solutions, Apps & AI/ML. Setting A, Residential [confirm against the brief] |
| 1. What problem are you solving? | Nobody can show a lender a defensible, site-level demand forecast before a mini-grid is built. Demand per customer varies about sevenfold (5 to 35 kWh a month), so systems end up oversized, undersized or never financed. |
| 2. Who does it benefit? | Developers who size systems, lenders and funders who finance them, and villagers whose tariff and reliability depend on a right-sized system. |
| 3. Value proposition | Developers size right before paying for a field survey. Lenders get a range and a chance-of-repayment they can check. Villagers get a fairer tariff. |
| 4. What is unique? | The brief names the gap: open, validated models that predict demand growth at a specific site with a credible range. DemandRange gives that range and growth from real coordinates, then turns it into a solar and battery size and the cost of getting it wrong. |
| Unit economics | About USD 259 per person connected (ESMAP: USD 127 billion for 490 million people). A village of 2,000 people is about USD 518,000 of capital, so each 10% sizing error is about USD 52,000 (assumes 400 connections of 5 people). Load factor 22% to 40% cut the cost of power by 25%. Real DRC study: about 9 kWh at USD 0.25 per kWh is about USD 2.25 a month, against about USD 13 a month spent on energy. |
| Impact metric | Error versus actual metered demand on held-out sites: [baseline ___ kWh to ___ kWh]. State whether simulated or real. |
| Sustainability | No moving parts. Report fees (price set in the pilot) cover hosting and yearly retraining. A named owner retrains it each year. Lowest-income affordability shown as bill vs current energy spend. |
| Feasibility | Runs today on free tools: OpenStreetMap, NASA POWER, open-source Python, free hosting. Evidence: [simulated / real]. |
| Scalability | Map and sunshine data exist for any country. Add a country by retraining on local meter data. The brief cites 177,000+ mappable settlements. |
| 6 to 18 month plan | Months 0 to 3: data agreements and real validation. Months 3 to 9: pilot on 3 to 5 sites with a developer and a lender. Months 9 to 18: open model, second country, named owner. |
| Prior work disclosure | See docs/disclosure_statement.md |
