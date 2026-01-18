# Paper Figures (Mermaid)

This folder contains paper-ready system architecture diagrams in Mermaid format.

## Files

- `docs/figures/system_architecture.mmd`: Runtime system overview (UI + central node + edge nodes + Docker + artifacts).
- `docs/figures/predictive_scheduling_pipeline.mmd`: Offline training + online inference pipeline for predictive scheduling.

## How to export for a paper

Option A (no local install): open https://mermaid.live, paste the file content, then export as **SVG** or **PDF**.

Option B (VS Code): install a Mermaid preview extension and export via the extension.

## Suggested figure captions (English)

**Figure: System architecture.** The Next.js digital-twin UI interacts with a Flask-based central node that manages datasets, assignment algorithms (greedy/optimization/predictive), and cluster-wide metrics. Edge nodes (cloudlets) run serverless functions inside Docker containers with cold/warm start behavior and periodically report metrics to the central node.

**Figure: Predictive scheduling pipeline.** A GRU-based mobility model is trained offline from T-Drive trajectories (optionally map-matched to OSM roads) and exported as artifacts. At runtime, the central scheduler loads these artifacts to infer per-user probabilities over candidate cloudlets and performs resource-aware predictive assignment.

