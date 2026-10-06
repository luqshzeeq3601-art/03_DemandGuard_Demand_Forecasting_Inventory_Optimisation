# 01. Problem and objectives

## 1. Problem statement

A small inventory planner has limited cash and storage. Products sell at different rates, demand changes over time, and supplier deliveries arrive later. A fixed reorder rule can purchase too many slow products while faster products run short.

The project asks: **Can a time-aware sales forecast support better weekly purchasing decisions than a simple reorder rule under the same constraints?**

This is a testable engineering hypothesis. The dataset alone does not prove that any retailer uses poor planning or has suffered a particular financial loss.

## 2. Users and decisions

| User | Decision | Useful output |
| --- | --- | --- |
| Inventory planner | What should I order this week? | Whole-unit quantities and product priorities |
| Operations manager | Can this plan fit our budget and warehouse? | Spend, capacity use and warnings |
| ML reviewer | Is the forecast reliable and repeatable? | Temporal backtests, baseline comparison and model card |
| Portfolio reviewer | Can the engineer turn ML into a working decision system? | Reproducible CLI/API, tests and scenario evidence |

## 3. Why this follows projects 1 and 2

- Adds forecasting and chronological evaluation to the portfolio.
- Adds SQL aggregation and product-level feature engineering.
- Adds mathematical optimisation rather than another classification app.
- Demonstrates a full chain: data -> forecast -> decision -> measured simulation outcome.
- The workbook maps this project to Mattel, DKSH, GAR and PetBacker. This mapping is source context, not evidence of current vacancies or employer adoption.

## 4. Objectives and measurement

| ID | Objective | Measurement and success rule |
| --- | --- | --- |
| O1 | Produce trustworthy weekly data | Immutable source, documented exclusions, complete panel, fixed cohort and reproducible split manifest |
| O2 | Forecast the next four weeks | All eligible SKU/horizon predictions finite and nonnegative; report WAPE, MAE and bias by fold, horizon and product |
| O3 | Test whether ML improves forecasting | Aim for at least 10% relative WAPE reduction against the strongest validation baseline; publish the actual comparison even if missed |
| O4 | Recommend feasible orders | Every executable order is a nonnegative integer; weekly spend and pre-demand storage remain within the declared constraints |
| O5 | Test inventory usefulness | Aim for at least 5% lower simulated total cost than the constrained rule policy without lower unit fill rate; disclose all scenario assumptions and actual outcomes |
| O6 | Deliver reproducible engineering | One documented local workflow, tracked experiments, passing relevant tests, API and Docker smoke evidence |
| O7 | Make future execution independent of chat | Specifications, task dependencies, commands, decisions and progress maintained in Markdown |

O3 and O5 are stretch hypotheses, not guaranteed release requirements. O1, O2, O4, O6 and honest reporting are mandatory engineering gates.

## 5. Metrics in simple terms

- **WAPE:** total absolute forecasting error divided by total actual units; lower is better. If actual units total zero, report unavailable and use MAE.
- **MAE:** average error in units; lower is better.
- **Bias:** signed total forecast error divided by total actual units. Positive means overforecasting.
- **Unit fill rate:** simulated fulfilled units divided by requested proxy-demand units; higher is better.
- **Simulated total cost:** purchase spend, holding cost, unmet-demand penalty and terminal inventory value adjustment as defined in the inventory specification.
- **Constraint violations:** invalid purchasing spend, storage or order quantities; must be zero for a successful plan.

## 6. Evidence limits

- Sales can understate true demand if stock was unavailable. Missing availability records prevent a causal claim about real stockouts.
- Initial stock, unit purchase costs, storage space, lead time and penalties are invented scenario inputs and must be labelled as such.
- UK benchmark results cannot establish effectiveness for Malaysian products, retailers or currency costs.
- A simulation estimates behaviour under its assumptions. It does not demonstrate realised revenue, savings or customer-service improvement.
- A four-week forecast from established products does not solve cold-start products or a changing catalogue.
