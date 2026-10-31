# Demand forecast memo: Sample village
*Prepared 2026-10-31 with DemandRange (prototype, simulated training data).*

## The short answer
In its first three years, each customer is likely to use about **21.1 kWh per month** (low case 17.1, high case 24.0). To cover its loan with a 1.2x safety margin, this site needs **19.8 kWh per customer per month**. We estimate a **69% chance** it gets there, so the loan is uncertain.

## How demand is expected to grow
| Year after connection | Low case | Middle case | High case |
|---|---|---|---|
| 0 | 13.7 | 16.3 | 19.7 |
| 1 | 16.1 | 20.0 | 22.7 |
| 2 | 17.5 | 21.3 | 24.2 |
| 3 | 17.8 | 22.1 | 25.0 |
| 4 | 17.8 | 22.1 | 25.0 |

## What drives the estimate
Change in the middle case (kWh per customer per month) if one input changes:
- Market nearby: remove it: -1.40
- Current monthly energy spending +20%: +0.50
- Number of households +20%: -0.50
- Businesses per 100 households +20%: +0.43

## Business customers and the cost of power
Estimated load factor: **36%**. That makes each kWh about **21% cheaper** than a households-only system (calibrated to the ESMAP figures in the brief).
Daytime customers worth signing first: Cold storage for market sellers; Grain milling or processing; Clinic vaccine fridge and school lighting (steady daytime load); Welding and carpentry workshops; Barbers, salons and phone charging.

## Can customers afford it?
At a tariff of $0.45 per kWh, the typical monthly bill is **$9.51**, which is **86%** of what households spend on candles, kerosene, batteries and diesel today.

## Assumptions (replace the placeholders before sharing)
- 400 customers; $600 build cost per customer (placeholder)
- $25 running cost per customer per year (placeholder)
- 70% debt at 10% over 10 years
- Annual loan payments: $27,341

## Where the inputs came from
- Entered by hand.

## Honest limits
This prototype was trained on simulated villages built from ranges in the problem brief. Its numbers show how the method works, not what any real site will do. Validate with real metered data before using it for a financing decision.