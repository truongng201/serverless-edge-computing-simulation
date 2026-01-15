# III. SYSTEM MODEL AND PROBLEM FORMULATION

## A. Network and Mobility Model

We consider a hierarchical **serverless edge** architecture composed of one central node (cloud) and a set of geo-distributed edge nodes (cloudlets). Time is discretized into simulation steps (indexed by \(t\)). At each step, a set of mobile users generates one serverless request that must be routed to exactly one compute node.

**Entities.** Let \(\mathcal{E}=\{1,\dots,E\}\) be the set of edge nodes and let \(0\) denote the central node. Define \(\mathcal{N}=\mathcal{E}\cup\{0\}\). Let \(\mathcal{U}(t)\) be the set of users active at step \(t\).

**Mobility model.** Each user \(u\in\mathcal{U}(t)\) has a 2D location \(\mathbf{p}_u(t)=(x_u(t),y_u(t))\) obtained from the dataset playback (e.g., TaxiD replay trajectories) or from synthetic generators. The simulator stores locations in pixel coordinates and uses a constant scale factor \(\delta\) to convert to meters:
\[
\delta = 10\ \text{m/pixel}.
\]
Each node \(n\in\mathcal{N}\) has a fixed location \(\mathbf{p}_n=(x_n,y_n)\) on the same map. The user–node Euclidean distance in meters is
\[
d_{u,n}(t)=\delta\sqrt{(x_u(t)-x_n)^2+(y_u(t)-y_n)^2}.
\]

**Network latency model.** For each request from user \(u\) routed to node \(n\), the end-to-end turnaround time is modeled as the sum of (i) propagation delay, (ii) transmission delay, and (iii) computation delay:
\[
T_{u,n}(t) = T^{\text{prop}}_{u,n}(t) + T^{\text{tx}}_{u}(t) + T^{\text{comp}}_{u,n}(t).
\]

1) **Propagation delay (4G deterministic).** The simulator uses a deterministic 4G LTE-inspired model with a base latency and a small distance-dependent term:
\[
T^{\text{prop}}_{u,n}(t)=L_0 + L_1\cdot \frac{d_{u,n}(t)}{1000},
\]
where \(L_0=48\) ms and \(L_1=0.01\) ms/km.

2) **Transmission delay.** The transmission delay is computed from the request payload size \(S_u\) (bytes) and the link bandwidth \(B\) (bytes/ms):
\[
T^{\text{tx}}_{u}(t) = \frac{S_u}{B}.
\]
In the default experiment configuration, \(S_u=512\) KB and \(B=3000\) bytes/ms (\(\approx 24\) Mbps).

3) **Computation delay (serverless cold/warm).** Computation delay depends on the container state at node \(n\). The simulator supports: (i) a **real** mode, where execution time is measured from actual container invocation, and (ii) a **simulated** mode, where execution time is assigned analytically to capture serverless cold-start behavior. In simulated mode, we model
\[
T^{\text{comp}}_{u,n}(t)=\tau^{\text{warm}}_n + \mathbb{I}^{\text{cold}}_{u,n}(t)\cdot \tau^{\text{cold}}_n,
\]
where \(\tau^{\text{warm}}_n\) is the warm execution baseline, \(\tau^{\text{cold}}_n\) is the additional cold-start penalty, and \(\mathbb{I}^{\text{cold}}_{u,n}(t)\in\{0,1\}\) indicates whether the request experiences a cold start (e.g., the user is not served on the same node as the previous execution and no prewarm applies). The default parameters are:
- Edge: \(\tau^{\text{warm}}_n=300\) ms, \(\tau^{\text{cold}}_n=1050\) ms
- Central: \(\tau^{\text{warm}}_0=300\) ms, \(\tau^{\text{cold}}_0=900\) ms

## B. Serverless Cost Model

The simulator evaluates routing decisions using a **latency-based cost** aligned with the optimization logic implemented in the central scheduler.

**Per-request cost.** The primary cost of assigning user \(u\) to node \(n\) at step \(t\) is the turnaround time \(T_{u,n}(t)\). To discourage routing to the central node when edge resources are available, the scheduler applies a multiplicative penalty \(w_n\):
\[
C_{u,n}(t)= w_n \cdot T_{u,n}(t),
\qquad
w_n=
\begin{cases}
1.2, & n=0\ (\text{central})\\
1.0, & n\in\mathcal{E}\ (\text{edge})
\end{cases}
\]
In the implementation, turnaround times may be normalized by \(\max_{u,n} T_{u,n}(t)\) for numerical stability during optimization, without changing the argmin assignment.

**Resource feasibility.** Each user has a memory demand \(m_u\) (default 128 MB). Each edge node \(n\in\mathcal{E}\) has an available memory budget \(M^{\text{avail}}_n(t)\) derived from its reported total memory and current usage. Assignments are considered feasible only if they satisfy capacity and health thresholds (e.g., CPU usage and memory usage below configured unhealthy thresholds).

## C. Problem Formulation (ILP)

At each step \(t\), the scheduler decides a user-to-node assignment that minimizes total cost under resource constraints.

**Decision variables.** Let
\[
x_{u,n}(t)\in\{0,1\}
\]
indicate whether user \(u\in\mathcal{U}(t)\) is assigned to node \(n\in\mathcal{N}\) at step \(t\).

**Objective.**
\[
\min_{x}\ \sum_{u\in\mathcal{U}(t)}\sum_{n\in\mathcal{N}} C_{u,n}(t)\,x_{u,n}(t).
\]

**Constraints.**

1) **Unique assignment (one node per user).**
\[
\sum_{n\in\mathcal{N}} x_{u,n}(t)=1,\qquad \forall u\in\mathcal{U}(t).
\]

2) **Memory capacity (edge and central).**
\[
\sum_{u\in\mathcal{U}(t)} m_u\, x_{u,n}(t)\le M^{\text{avail}}_n(t),\qquad \forall n\in\mathcal{N}.
\]
In the simulator, \(M^{\text{avail}}_0(t)\) for the central node is treated as a very large constant (effectively “unlimited”).

3) **Feasibility constraints (optional explicit form).** Let \(\mathcal{F}_u(t)\subseteq\mathcal{N}\) be the set of nodes that satisfy health/resource checks for user \(u\) at step \(t\) (e.g., CPU and memory usage below thresholds). Then:
\[
x_{u,n}(t)=0,\qquad \forall u\in\mathcal{U}(t),\ \forall n\notin\mathcal{F}_u(t).
\]

**Implementation note (relation to code).** The current scheduler implementation solves a relaxed version with \(x_{u,n}(t)\in[0,1]\) using `cvxpy`, then assigns each user to the node with the largest relaxed value while re-checking feasibility. The ILP above matches the same objective/constraints but enforces integrality.

