# DemandGuard workflow image

Asset: [workflow.png](workflow.png). Generated with the built-in OpenAI image-generation tool on 6 October 2026 and reviewed against the project source. Style: modern light theme, warm white background, navy text and teal accents. This is an architecture illustration, not a screenshot or measured result chart.

## Meaning and source

The README supplies the accessible text summary and links to the owning technical/data/protocol documents. Model metrics remain sourced from the saved analytical artifacts. The diagram does not certify deployment or operational impact.

## Generation prompt

```text
Use case: infographic-diagram. Asset type: a GitHub README workflow image. Wide landscape 2:1, at least 1600 pixels wide. Modern light theme: warm white background, navy text, restrained teal accents, flat rounded cards, thin clean arrowheads, original small line icons, generous whitespace. No dark panels, gradients, logos, watermarks or fake screenshots. Large readable typography at a 900-pixel display width. Use EXACT labels given below. Explain implemented source architecture; do not invent metrics, successful deployment, automatic retraining or measured commercial impact.
Exact title: "DemandGuard". Exact subtitle: "From weekly sales to constrained reorder decisions".
Main path: "Retail transactions" -> "Weekly panel + causal features" -> "Four-week forecasts" -> "PuLP + CBC optimizer" -> "Validated integer orders".
A separate small card labelled "Budget + capacity + lead time" feeds ONLY the optimizer.
From "Validated integer orders", a clear downwards branch feeds "Inventory simulation", which points to "Cost + fill-rate evaluation".
A small supporting note attached to the forecasts says "Compare baselines + LightGBM".
Footer: "Chronological evaluation" and "Simulated costs are scenario units".
Constraints: no numeric improvement claim and no suggestion that the ML forecast or policy beats its baseline. The optimizer's feasibility checks precede the order output. Diagram may use two rows but preserve the specified connections and leave room for all exact labels.
```
