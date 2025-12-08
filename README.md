**Course: ECE1779 – Introduction to Cloud Computing (Fall 2025)**

**Project Title: Cloud-Native Network Health Dashboard**

## **1. Author Information:**

\- Diana Sofia Chamorro Zuleta

\- Student Number: 1003126100

\- Email: dianas.chamorro@gmail.com  

This is an individual project; all design and implementation work described in this report was completed by the single team member listed above.

## **2. Motivation**

**2.1 Problem Background**

Modern applications depend on reliable network connectivity. For large telecom operators and global cloud providers, uptime and latency are mission-critical indicators of service health. They invest in advanced observability platforms, such as Datadog or Cisco ThousandEyes, that offer real-time dashboards, alerting pipelines, and deep historical analytics. These platforms are incredibly powerful but also expensive, complex to deploy, and tightly coupled to proprietary ecosystems.

In my experience as a network engineer, I have seen firsthand how essential these tools are in day-to-day operations: they allow engineers to detect incidents within seconds, correlate failures with infrastructure changes, and maintain exceptional quality of experience for end users.

However, there is a clear gap that remains unaddressed. Students, individual developers, and small organizations also deploy websites, APIs, and microservices. They still care about uptime and performance but they rarely have access to enterprise-grade observability platforms or the capacity to configure multi-tool monitoring stacks. At the end of the day, they are asking the same fundamental questions as any large provider: *Is my service up or down? How fast is it responding? Has its performance changed over time? And can I be notified when something breaks?*

**2.2 Motivation for This Project**

The goal of this project is to address that gap by developing a lightweight, cloud-native, and educational network health dashboard. The system is intentionally designed to be simple, transparent, and fully open so that it can serve both practical monitoring needs and as a learning resource. Specifically:

- Simple and user-friendly: Users should be able to sign up, register endpoints, and immediately visualize uptime and latency trends without complex configuration.
- Fully cloud-native: All components are containerized, orchestrated with Kubernetes, and backed by a persistent PostgreSQL database, reflecting modern industry practices.
- Transparent and inspectable: The entire codebase is available in an open GitHub repository, making it easy for students, developers, and instructors to study, extend, or reuse the system as a reference implementation.

This project is also a way to connect my professional background (network design and performance) with the core technologies of the course: Docker, Kubernetes, PostgreSQL, and cloud deployment on DigitalOcean. Rather than building a toy example, I wanted a project that I would genuinely use to monitor my own lab endpoints and that could be extended later (e.g., email notifications, predictive alerts, or more advanced analytics).
## **3. Objectives**
This project was designed with two complementary sets of goals: those directed toward the end-user experience, and those focused on the technical implementation and cloud-native requirements.
**3.1 User-Facing Objectives**
From the perspective of an end user, the system should provide a secure and intuitive experience for monitoring web services. Users must be able to register an account, authenticate, and manage only the endpoints that belong to them. Once authenticated, they should be presented with a clean dashboard interface through which they can add, edit, and delete HTTP endpoints while easily viewing the most recent status and latency of each one. The interface should also allow users to manually trigger endpoint checks on demand.

Beyond the immediate status, the application should offer rich insights into historical performance through a detailed endpoint view. This includes access to measurement history, a 24-hour latency visualization using a line chart, and discovery of aggregated statistics such as uptime percentage and average latency. Because service health can fluctuate over time, each user must be able to configure alert conditions for every endpoint, specifying thresholds for latency and for consecutive failures. The application should also maintain and display a timeline of alert events so that users can understand when and why alerts were triggered.

Finally, the system should remain accessible in both local and cloud environments. Users should be able to run the application locally using Docker Compose or access it through its cloud deployment on DigitalOcean Kubernetes, without needing deep knowledge of cluster operations or infrastructure tools.
**3.2 Technical Objectives**
From a technical standpoint, the project aims to serve as a practical demonstration of modern, cloud-native architectural principles. The system adopts Docker and Docker Compose to support a multi-service development environment composed of a FastAPI backend, a worker service, a frontend application, and a PostgreSQL database.

Persistent storage is a core requirement: PostgreSQL must retain state across container restarts and redeployments, ensuring that user accounts, endpoints, measurements, and alerts are durable. The backend exposes a RESTful API with JWT-based authentication, password hashing, and full CRUD functionality for endpoints, in addition to endpoints for ingesting and retrieving measurements as well as computing uptime statistics and alert configurations.

A separate worker service is responsible for continuously checking registered endpoints in the background, recording results in the database, and applying the alert logic. All components are deployed to DigitalOcean Kubernetes using Deployments and Services to ensure modularity and scalability, with a dedicated PersistentVolumeClaim providing reliable database storage. Namespaces and Secrets are used to isolate and configure the environment securely.

Monitoring and observability play an important role in validating system behavior. Infrastructure-level visibility is provided through DigitalOcean’s built-in metrics (CPU, RAM, storage, and pod restarts), while application-level monitoring is exposed directly within the dashboard through calculated uptime, latency trends, and alert state. To satisfy advanced course requirements, the system also incorporates two higher-level features: a robust JWT-based security layer and an automated CI/CD workflow using GitHub Actions to build container images for deployment to the DigitalOcean Container Registry.
## **4. Technical Stack**
The platform is implemented as a small, cloud-native system composed of four cooperating services:

- **FastAPI backend**: which exposes a REST API with JWT authentication and provides all user-facing data operations.
- **Python worker service**: which executes continuous background health checks and evaluates alert conditions.
- **React + Vite frontend**: which serves as the interactive dashboard for visualizing status, latency trends, and alert history.
- **PostgreSQL database**: which stores all durable state, including users, endpoints, measurements, and alerts.

All services are containerized using Docker and orchestrated through Kubernetes on DigitalOcean Kubernetes (DOKS). Image artifacts are stored in the DigitalOcean Container Registry, while persistent state is backed by a Kubernetes PersistentVolumeClaim using DigitalOcean Block Storage.
**4.1 Orchestration Layer: Kubernetes on DigitalOcean**
Kubernetes was selected as the orchestration framework (instead of Docker Swarm) to provide declarative deployments, automated rollouts, service discovery, and persistent storage integrations.

The deployment structure includes:

- A dedicated namespace (network-dashboard) to isolate project resources.
- A replicated API Deployment (2 pods) exposed internally through a ClusterIP Service.
- A Worker Deployment (1 pod) responsible for periodic background checks.
- A PostgreSQL Deployment anchored to a PersistentVolumeClaim for durable storage.
- A Frontend Deployment exposed externally via a LoadBalancer/NodePort Service.

Each service receives configuration via Kubernetes environment variables (e.g., database credentials, polling intervals), allowing identical images to run seamlessly in both local and cloud contexts. Kubernetes manages pod placement, scaling, and restart behavior, ensuring the system remains modular and resilient.
**4.2 Backend API: FastAPI, JWT Security, and Direct SQL Access**
The backend is implemented in FastAPI, chosen for its performance, simplicity, and strong typing. It provides all core application functionality:
**Authentication and Access Control**
- JWT authentication using python-jose and OAuth2PasswordBearer.
- Password hashing with passlib (PBKDF2-SHA256).
- Signed tokens include user identifiers and expiration timestamps.
- A shared dependency (get\_current\_user) validates tokens and enforces per-user resource isolation.

This mechanism ensures that users can only access their own endpoints and monitoring data.
**Database Interaction**
The backend uses psycopg with dict\_row to return rows as Python dictionaries.\
Connection parameters are provided via environment variables:

DB\_HOST, DB\_PORT, DB\_NAME, DB\_USER, DB\_PASSWORD

The lightweight “connection-per-request” design is appropriate for the project’s scale and keeps data access explicit. No ORM is used, giving full transparency over SQL execution.
**API Structure**
The backend supports:

- User management (/signup, /login)
- Endpoint CRUD operations
- Measurement ingestion and retrieval
- Statistics computation (uptime %, average latency)
- Manual endpoint checks
- Alert configuration and alert history

A /healthz endpoint enables Kubernetes to perform liveness/readiness checks.
**4.3 Background Worker: Continuous Monitoring and Alert Evaluation**
The worker is a standalone Python service running in its own Deployment. It implements the background logic for health monitoring:
**Runtime Behavior**
Every polling cycle (default: 60 seconds), the worker:

1. Fetches all registered endpoints and alert settings from PostgreSQL.
1. Performs an HTTP GET request for each endpoint, measuring latency.
1. Inserts a new measurement record into the database.
1. Updates alert state based on latency thresholds and consecutive failures.
1. Generates alert records when conditions are met.
1. Commits the transaction and sleeps until the next cycle.
**Alert Logic**
Alerts are triggered under two conditions:

- **Consecutive failures**: exceeding consecutive\_fail\_threshold
- **High latency**: exceeding latency\_threshold\_ms

Alerts remain active until the endpoint returns to a healthy state.\
This stateful logic is stored directly in the endpoints table to maintain consistency across worker restarts.
**4.4 Database Layer: PostgreSQL with Durable Storage**
PostgreSQL stores all persistent application data across four core tables:

- users (accounts and password hashes)
- endpoints (URLs, thresholds, alert state)
- measurements (latency + status per check)
- alerts (alert events with timestamps and values)

In local development, persistence is handled with a Docker volume and init.sql initialization.\
In Kubernetes, a **PersistentVolumeClaim** ensures data durability across pod restarts and redeployments.

This schema-first, explicit-SQL approach keeps the system transparent and easy to extend.
**4.5 Frontend: React, Vite, and Chart.js**
The frontend is implemented as a React single-page application powered by Vite for rapid iteration and optimized builds. Its responsibilities include:

- User authentication and token storage.
- CRUD operations for endpoints.
- Triggering immediate endpoint measurements.
- Rendering tables for summary, history, and alerts.
- Visualizing latency trends using Chart.js line graphs.
- Managing alert configuration inputs.

The UI emphasizes clarity and mirrors the structure of real monitoring dashboards.
**4.6 Containerization and Local Development: Docker & Compose**
Local development uses Docker Compose, which orchestrates:

- api (FastAPI backend)
- worker (background service)
- frontend (React application)
- postgres (database + initialization script)

All services share a consistent environment variable model with the Kubernetes deployment.\
This makes local testing predictable and mirrors production conditions closely.
**4.7 Cloud Platform and Monitoring: DigitalOcean**
The production deployment runs entirely on DigitalOcean:

- DigitalOcean Kubernetes (DOKS) hosts the cluster.
- DigitalOcean Container Registry stores all images.
- DigitalOcean Block Storage backs PostgreSQL persistence.
- Metrics and logs from DOKS provide node and pod visibility (CPU, memory, events, restarts).

Application-level monitoring is integrated directly into the dashboard, including:

- Uptime percentage
- Latency statistics
- Measurement history
- Alert state

Together, these provide both infrastructure-level and application-level observability.

## **5. Features**

The application provides a complete, cloud-native Network Health Dashboard that enables authenticated users to monitor the availability, performance, and alert status of their HTTP endpoints. Its functionality spans user authentication, endpoint configuration, real-time and historical monitoring, alert management, and continuous background checks. Together, these features fulfill the project’s objectives and the course’s requirements for cloud-native architecture, persistent storage, monitoring, and containerized deployment.

**5.1 User Authentication and Multi-Tenancy**

Users authenticate through the frontend using email and password credentials, which are securely transmitted to the FastAPI backend. The backend verifies password hashes, issues JSON Web Tokens (JWT), and applies token-based authorization to all protected routes.

The system enforces strict per-user isolation: each user can only access their own endpoints, measurements, and alerts. JWTs are stored locally in the browser and attached to each request, ensuring a seamless and secure session flow.

This feature demonstrates secure backend logic, stateful user management, and the ability to support multiple independent user accounts—fundamental aspects of a realistic cloud-native service.

**5.2 Endpoint Management Dashboard**

After authentication, users access the central dashboard where they can configure the endpoints they wish to monitor. The dashboard provides:

- The ability to create new endpoints by specifying a name and URL.
- A table listing all endpoints owned by the user, along with metadata such as creation time.
- Per-endpoint actions including immediate measurement, deletion, and access to a more detailed analytics view.

This implements CRUD-style resource management and supports the objective of creating a simple, intuitive interface that allows monitoring to begin immediately after signup.

**5.3 Summary View: Real-Time Status and Alerts**

The Summary view presents the latest state of all monitored endpoints. Data is retrieved from the backend summary endpoint and includes:

- Endpoint identifiers, names, and URLs.
- Latest status (UP/DOWN/UNKNOWN).
- Most recent latency measurement.
- Timestamp of the last successful check.
- Active alert indicators displayed through color-coded badges.

This view represents the core monitoring functionality, providing users with a quick operational overview of endpoint health using data generated by the worker and exposed by the API.

**5.4 Detailed Endpoint View: History, Statistics, and Visualization**

Selecting an endpoint reveals an analytics panel powered by multiple backend endpoints. This view includes:

**a. 24-Hour Statistics:** Derived from the statistics endpoint, the dashboard displays uptime percentage, average latency, and the total number of checks for the selected time window.

**b. Latency Visualization:** A line chart rendered with Chart.js visualizes latency trends, allowing users to detect anomalies, performance degradation, or outages.

**c. Measurement History:** A tabular view provides recent observations, including timestamps, status, and latency.** This feature supports historical monitoring and data visualization, key components in building an educational, transparent cloud-native monitoring tool.

**5.5 Configurable Alerts and Alert History**

Each endpoint includes a configurable alerting panel, enabling users to define:

- Maximum acceptable latency (in milliseconds).
- The number of consecutive failures required before declaring downtime.

The UI also displays real-time alert state, including active alerts, consecutive failure counters, and the time the last alert was triggered.

A complementary alert history table lists recent events, describing their type (latency or downtime) and corresponding messages and values.

Configurable alerting demonstrates a stateful feature spanning backend logic, worker behavior, and frontend presentation, illustrating how distributed cloud components collaborate to implement “smart alerts.”

**5.6 Continuous Background Monitoring**

Independent of user interaction, the worker service performs periodic health checks on all registered endpoints. It measures latency, classifies availability, inserts measurements, evaluates alert thresholds, and logs alert events.

This feature demonstrates separation of concerns between interactive traffic (API) and asynchronous background processing, fulfilling the requirement for continuous monitoring and enabling accurate uptime and alert calculations.

**5.7 Manual Measurements**

In addition to automated checks, users may request immediate measurements. The “Measure” action invokes the backend’s measurement endpoint, triggering an on-demand HTTP check whose results are immediately incorporated into the dashboard’s summary and detail views.

Manual measurement enhances usability, supports debugging workflows, and reflects real-world monitoring tools that combine scheduled and on-demand checks.

**5.8 Cloud-Native and Persistent User Experience**

Several architectural decisions manifest as user-visible features:

- State persists across pod restarts due to PostgreSQL backed by a PersistentVolumeClaim.
- The API runs with multiple replicas, improving availability and demonstrating stateless scaling principles.
- The dashboard is accessible through the live Kubernetes deployment on DigitalOcean (as documented in the Deployment Information section).

These features directly satisfy course requirements for Docker, PostgreSQL, persistent storage, Kubernetes orchestration, monitoring, and cloud deployment. They also reinforce the project’s goal of providing a simple yet realistic cloud-native reference system.

# **6.  User Guide**
This section explains how a user interacts with the Network Health Dashboard, from logging in to monitoring uptime, reviewing historical data, and configuring smart alerts. The application is available online at:  [**http://209.38.10.37**](http://209.38.10.37/)
**6.1. Accessing the Application**
Open any modern browser (Chrome, Edge, Firefox, Safari) and navigate to: <http://209.38.10.37>

![A screenshot of a computer&#x0A;&#x0A;AI-generated content may be incorrect.](Aspose.Words.610d5a1f-f79a-4cba-bd4a-489d762d51d3.001.png)

<IMAGEN DE LOGIN>

**6.2. Creating an Account (Sign Up)**

New users may register for an account directly from the login page:

1. Select **Sign Up**.
1. Enter an email address and password.
1. Click **Create**.

The frontend submits the credentials to the /signup endpoint. Upon successful registration, the backend issues a JSON Web Token (JWT), which is stored in the browser’s localStorage. Users are then redirected automatically to the dashboard.
**6.3. Logging In**
Existing users authenticate by providing their credentials on the login form:

1. Enter email and password.
1. Click **Login**.

If the credentials are valid, the backend returns a JWT and the dashboard loads. Invalid credentials produce a clear error message. The stored token is attached automatically to all subsequent authenticated API requests.
**6.4. Main Dashboard Overview**
After logging in, you land on the Network Health Dashboard**.**

The dashboard contains:

- A header with the app title and a Logout button.
- A form to add new endpoints.
- A table listing all your endpoints.
- A Summary section showing the latest health status and latency.

<IMAGEN 1 DE DASHBOARD>

<IMAGEN 2 DE DASHBOARD>

![A screenshot of a dashboard&#x0A;&#x0A;AI-generated content may be incorrect.](Aspose.Words.610d5a1f-f79a-4cba-bd4a-489d762d51d3.002.png)![A screenshot of a computer&#x0A;&#x0A;AI-generated content may be incorrect.](Aspose.Words.610d5a1f-f79a-4cba-bd4a-489d762d51d3.003.png)
**6.5. Adding a New Endpoint**
To begin monitoring a website or service:

1. In the **Add new endpoint** section, enter:
   1. Name** (e.g., “Google”)
   1. URL** (e.g., https://www.google.com)
1. Click **Add**.

Your new endpoint appears immediately in the list and summary.
**6.6. Viewing Your Endpoint List**
The **Your endpoints** section shows all endpoints you own.

Columns include:

- ID
- Name
- URL
- Creation Timestamp
- Actions (Measure, Delete, Details)
**Actions:**
- ***Measure:*** Triggers an immediate health check via */api/endpoints/{id}/measure.*
- ***Delete:*** Removes an endpoint permanently.
- ***Details:*** Opens the detailed monitoring view (history, stats, alerts).
***<IMAGEN DE ENDPOINTS TABLE>***

**6.7. Summary View: Real-Time Status**
The **Summary** table uses /api/endpoints/summary to display:

- Name & URL
- **Status** (UP, ALERT)
- Latest latency (ms)
- Last observed time

A color-coded badge indicates the state:

- 🟢 **UP**
- 🔴 **ALERT**

***<IMAGEN DE SUMARY TABLE>***

![A screenshot of a computer&#x0A;&#x0A;AI-generated content may be incorrect.](Aspose.Words.610d5a1f-f79a-4cba-bd4a-489d762d51d3.005.png)

**6.8. Opening the Detailed View**

Click **Details** on any endpoint to open the full monitoring panel.

***<IMAGEN DE DETAILS>***

![A screenshot of a graph&#x0A;&#x0A;AI-generated content may be incorrect.](Aspose.Words.610d5a1f-f79a-4cba-bd4a-489d762d51d3.006.png)

The detailed view contains:

1. 24-hour stats
1. Alert configuration panel
1. Latency line chart
1. Measurement history table
1. Recent alerts table
**6.9. Uptime & Latency Statistics**
At the top of the detailed view, the app displays:

- Uptime %
- Average latency (ms)
- Number of checks in the time window
- Window duration (default 24h)

Data comes from: /api/endpoints/{id}/stats?hours=24
**6.10. Configuring Alerts**
Alerts are fully customizable per endpoint.

You can configure:

- Latency threshold (in ms)
- Consecutive failure threshold (number of ‘down’ checks required)

You also see:

- Current consecutive failures
- Whether an alert is active
- Timestamp of last alert

Updating the configuration calls: PUT /api/endpoints/{id}/alert-config
**6.11. Latency Visualization (Chart.js)**
A detailed latency trend graph is presented using **Chart.js**, showing:

- Time on the horizontal axis
- Latency (ms) on the vertical axis
- Smooth curve for easy interpretation

Data source: /api/endpoints/{id}/measurements?limit=50

**6.12. Measurement History Table**

Below the chart, users see the raw measurement data:

- Time of check
- Status (up/down)
- Latency (ms)

This enables debugging and correlation with incidents.

***<IMAGEN DE HISTORY TABLE>***

![A screenshot of a computer&#x0A;&#x0A;AI-generated content may be incorrect.](Aspose.Words.610d5a1f-f79a-4cba-bd4a-489d762d51d3.007.png)
**6.13. Alert History**
If alerts have been triggered for the endpoint, they appear at the bottom of the page:

- When the alert happened
- Type of alert (down or latency)
- Message
- Optional numeric value (latency exceeded)

***<IMAGEN DE ALERT SUMMARY TABLE>***

## ![A screenshot of a computer&#x0A;&#x0A;AI-generated content may be incorrect.](Aspose.Words.610d5a1f-f79a-4cba-bd4a-489d762d51d3.008.png)
**6.14. Logging Out**
Click **Logout** on the top-right to:

- Remove your token from localStorage
- Clear all state
- Return to the login page

**6.15. Summary of User Flow**

1. Visit the deployment URL.
1. Sign up or log in.
1. Add endpoints to monitor.
1. Track their current health in the Summary table.
1. Open Details for deeper insights (history, charts, stats).
1. Configure alerts for latency or downtime.
1. Monitor alert history and system behavior over time.
1. Log out anytime.
## **7. Development Guide**
This section explains how to set up the development environment, including the application services, database, storage, and local testing workflow. The recommended way to run the project locally is via Docker Compose**,** which closely mirrors the Kubernetes deployment.

**7.1 Prerequisites**

Before running the system locally, ensure the following tools are installed:

- Git
- Docker and Docker Compose (Docker Desktop on macOS/Windows)
- kubectl for interacting with the DigitalOcean Kubernetes cluster
- *(Optional)* Python 3.12+ for running the backend or worker directly
- *(Optional)* Node.js + npm for running the frontend development server

These tools allow the project to be executed via container orchestration or through standalone processes.


**7.2. Repository Structure (High-Level)**
A typical layout for the project:

***<IMAGEN DE REPOSITORYTABLE>***

![A screenshot of a computer&#x0A;&#x0A;AI-generated content may be incorrect.](Aspose.Words.610d5a1f-f79a-4cba-bd4a-489d762d51d3.009.png)

- backend/ contains the FastAPI application.
- worker/ contains the background monitoring loop.
- frontend/ contains the React + Vite dashboard.
- initdb/init.sql initializes the PostgreSQL schema.
- k8s/ stores the Kubernetes manifests for cloud deployment.
- docker-compose.yml orchestrates all services locally.


**7.3 Environment Configuration**
Both the backend and worker read their configuration from environment variables.

**Backend Configuration (FastAPI)**
Key environment variables include:

DB\_HOST

DB\_PORT

DB\_NAME

DB\_USER

DB\_PASSWORD

JWT\_SECRET\_KEY

Typical local values (via Docker Compose) are:

DB\_HOST=postgres

DB\_PORT=5432

DB\_NAME=nethealth

DB\_USER=netuser

DB\_PASSWORD=netpass

JWT\_SECRET\_KEY=some-local-secret

These values determine database connectivity and authentication behavior.

**Worker Configuration**
From worker.py, the worker service uses:

DB\_HOST

DB\_PORT

DB\_NAME

DB\_USER

DB\_PASSWORD

POLL\_INTERVAL\_SECONDS

HTTP\_TIMEOUT\_SECONDS

Local development commonly uses:

DB\_HOST=postgres

POLL\_INTERVAL\_SECONDS=60

HTTP\_TIMEOUT\_SECONDS=5.0

**Frontend Configuration**
The frontend uses Vite’s environment variables:

import.meta.env.VITE\_API\_BASE\_URL

Examples:

VITE\_API\_BASE\_URL=http://localhost:8000

VITE\_API\_BASE\_URL=http://api:8000

VITE\_API\_BASE\_URL=http://209.38.10.37:8000

This determines where the frontend sends API requests.


**7.4. Local Development**
Developers can test the full system locally using Docker Compose:

1. Clone the repository.
1. Run:
1. docker compose up --build
1. Access the services:
   1. Frontend: http://localhost:5173
   1. Backend docs: http://localhost:8000/docs

PostgreSQL is automatically initialized with initdb/init.sql on first startup, and data persists via Docker volumes.

Local execution allows developers to rapidly test authentication, endpoint configuration, measurement ingestion, alert logic, and frontend interactions before publishing changes to the cloud.



**7.5 Local Testing Workflow**

**7.5.1 Using the UI**
1. Run docker compose up --build.
1. Open the frontend (e.g., http://localhost:5173).
1. Create an account and log in.
1. Add endpoints such as:
   1. https://www.google.com
   1. a test API
   1. an endpoint that returns error codes for alert testing
1. Observe:
   1. Summary table updates
   1. Detailed view (charts, stats, measurement history)
   1. Alert history

**7.5.2 Using FastAPI Interactive Docs**
Navigate to: <http://localhost:8000/docs>

From here, you can:

- Test **/**signup, /login
- Authenticate using the Authorize button
- Call protected endpoints:
  - /api/endpoints
  - /api/endpoints/summary
  - /api/endpoints/{id}/measurements
  - /api/endpoints/{id}/stats
  - /api/endpoints/{id}/alert-config

This is useful for backend debugging without involving the UI.

**7.5.3 Observing Worker Logs**
docker compose logs -f worker

Example output:

[worker] Checking 3 endpoints...

[worker] Google (...) -> status=up, latency=85ms

[worker] Test API (...) -> status=down, latency=None

[worker] Sleeping for 60 seconds...

These logs confirm correct measurement and alert generation

**7.6 Production Deployment Workflow**
The system is designed primarily for Kubernetes deployment. DigitalOcean Kubernetes (DOKS) is used for production, following a declarative and repeatable deployment workflow.

**Container Images**
Each component (backend, worker, and frontend) is built as a Docker image and stored in th**e** DigitalOcean Container Registry (DOCR)**.** A GitHub Actions CI/CD pipeline automatically:

- Builds images on each push to main
- Tags them with the commit SHA
- Pushes them to DOCR


**Kubernetes Manifests**
The k8s/ directory includes manifests defining:

- Deployments** for backend (replicated), worker, frontend, and PostgreSQL
- Services for communication and Public Access
- PersistentVolumeClaim (PVC)** for durable PostgreSQL storage
- Namespace: network-dashboard

Apply all manifests using:

kubectl apply -f k8s/ -n network-dashboard


**Runtime Behavior in Production**
- The API** runs as a replicated Deployment (2 pods) to improve availability.
- The worker** runs continuously in a separate Deployment.
- PostgreSQL** persists data on a Block Storage–backed PVC.
- The frontend** is exposed through a Kubernetes Service, enabling public access.

Operational visibility is provided through both DigitalOcean metrics (CPU, memory, restarts) and application-level monitoring within the dashboard.


**7.7 Cloud Storage and Persistence**
In production, PostgreSQL uses a PersistentVolumeClaim** attached to a DigitalOcean Block Storage volume. This ensures:

- User data and measurements persist across pod restarts and rolling updates
- Application state remains stable during node maintenance
- Resetting the database requires deliberate PVC removal

This fulfills the project’s requirement for reliable, persistent storage.


**7.8 Production Testing and Verification**
Testing and verification in the cloud environment use:

- kubectl logs for backend, worker, and frontend
- The DigitalOcean Kubernetes dashboard for cluster metrics
- The web application for end-to-end testing of uptime, latency charts, and alerts
- FastAPI’s /docs interface for verifying API behavior

This combination provides both infrastructure-level and application-level diagnostics.


## **8. Deployment Information**
This project is fully deployed on a DigitalOcean Kubernetes (DOKS) cluster, using container images stored in the DigitalOcean Container Registry (DOCR)** and automatically updated through a GitHub Actions CI/CD pipeline. The deployment mirrors modern cloud-native production environments by relying on Kubernetes for orchestration, scalability, and service isolation.

All workloads run inside the dedicated namespace **network-dashboard**, and all manifests are defined declaratively in the **k8s/** directory of the repository.

**8.1 Workloads Running in Production**
The deployed system consists of four primary components:

- **Api**: FastAPI backend (Deployment, 2 replicas)
- **Worker**: Background measurement processor (Deployment, 1 replica)
- **Frontend**: React single-page application (Deployment, 1 replica)
- **Postgres**: Stateful PostgreSQL instance with PersistentVolumeClaim (1 replica)

Kubernetes Deployments, Services, Secrets, and PVCs collectively ensure that each component is isolated, resilient, and independently manageable.


**8.2 Live Application URL**
The application is publicly accessible at: [http://209.38.10.37](http://209.38.10.37/)

This external address is automatically provisioned by DigitalOcean as part of the LoadBalancer Service exposing the frontend.

- The frontend is reachable publicly.
- The backend API**,** worker**,** and PostgreSQL are accessible only inside the cluster** through Kubernetes Service networking.

This separation ensures secure internal communication between services while exposing only the UI to the public internet.


**8.3 Deployment Workflow**


**1. Applying Kubernetes Manifests**
The entire application stack is deployed with a single command:

kubectl apply -f k8s/ -n network-dashboard

This applies, in order:

- namespace.yaml — Creates the namespace
- do-registry-secret.yaml — Credentials for pulling images from DOCR
- postgres.yaml — Stateful database + PersistentVolumeClaim
- api-service.yaml — Backend Deployment + Service
- api-worker.yaml — Worker Deployment
- frontend.yaml — Frontend Deployment + LoadBalancer Service
- sa-patch.yaml — Additional permissions required for image pulling

DigitalOcean then provisions a public IPv4 address for the frontend LoadBalancer.

**2. Continuous Deployment with GitHub Actions**
A full CI/CD pipeline, defined in .github/workflows/deploy.yml, automates build and deployment processes.

Whenever new code is pushed to **main**, the pipeline performs:

#### ***a) Docker image build***
Each component is built and tagged with the Git commit SHA:

docker build -t $REGISTRY/api:${IMAGE\_TAG} ./backend

docker build -t $REGISTRY/frontend:${IMAGE\_TAG} ./frontend

docker build -t $REGISTRY/worker:${IMAGE\_TAG} ./worker

#### ***b) Push to DigitalOcean Container Registry***
docker push $REGISTRY/api:${IMAGE\_TAG}

docker push $REGISTRY/frontend:${IMAGE\_TAG}

docker push $REGISTRY/worker:${IMAGE\_TAG}

#### ***c) Authentication to the Kubernetes cluster***
echo "${{ secrets.KUBE\_CONFIG }}" > ~/.kube/config
#### ***d) Rolling update of Kubernetes Deployments***
kubectl set image deployment/api api=$REGISTRY/api:${IMAGE\_TAG} -n network-dashboard

kubectl set image deployment/frontend frontend=$REGISTRY/frontend:${IMAGE\_TAG} -n network-dashboard

kubectl set image deployment/worker worker=$REGISTRY/worker:${IMAGE\_TAG} -n network-dashboard
#### ***e) Rollout verification***
kubectl rollout status deployment/api -n network-dashboard

kubectl rollout status deployment/frontend -n network-dashboard

kubectl rollout status deployment/worker -n network-dashboard

This ensures that every commit triggers a complete rebuild, redeploy, and automated verification of the production environment.

**8.4 Database Deployment & Persistent Storage**
The PostgreSQL database runs as a Kubernetes Deployment backed by a PersistentVolumeClaim mapped to DigitalOcean Block Storage. This guarantees:

- Durable storage for users, endpoints, measurements, and alerts
- Safety across pod restarts, upgrades, and node rescheduling
- Predictable performance in production environments

The backend and worker connect internally through:

postgres.network-dashboard.svc.cluster.local

ensuring secure, cluster-private communication.

**8.5 Summary**
The application is deployed as a fully cloud-native system using:

- DigitalOcean Kubernetes (DOKS) for orchestration
- DigitalOcean Container Registry (DOCR) for image hosting
- GitHub Actions CI/CD for automated builds and rollouts
- Persistent storage via DigitalOcean Block Storage
- Load-balanced frontend for public access
- Internal-only backend, worker, and database for security and modularity

This architecture fulfills the course requirements for:

- Containerization
- Multi-service application design
- Kubernetes orchestration
- Persistent storage
- Cloud deployment
- Advanced features (CI/CD automation)

## **Individual Contributions**
I completed this entire project on my own. I designed and built every part of the system—from the FastAPI backend and background worker, to the React frontend, PostgreSQL database, Docker setup, and all Kubernetes deployments. I also configured the CI/CD pipeline, created the cloud infrastructure on DigitalOcean, and handled all debugging, testing, and integration work myself. The Git commit history reflects this full end-to-end ownership of the project

## **Lessons Learned and Concluding Remarks**
Developing this project provided meaningful hands-on experience with cloud-native application design, Kubernetes orchestration, and full-stack system integration. One of the key lessons learned was the importance of separating components into independent, well-defined services. Implementing the backend API, the worker, and the frontend as distinct containers allowed the system to behave predictably both locally and in the cloud, and reinforced the value of modular architecture when deploying real applications.

Working with Kubernetes highlighted the significance of declarative configuration, environment-based settings, and proper service isolation. Concepts such as Deployments, Services, PersistentVolumeClaims, and image pull secrets became clearer through practical use rather than theoretical study alone. The DigitalOcean deployment process also emphasized the need for robust observability—pod logs, metrics, and rollout status checks were essential tools throughout development.

Another major learning outcome was implementing authentication and alerting logic in a production-oriented way. Designing JWT-based authentication, stateful alert thresholds, and continuous background processing helped bridge distributed-system concepts with user-facing functionality. Additionally, setting up CI/CD through GitHub Actions provided valuable insight into automating build and deployment pipelines, mirroring industry workflows.

Overall, this project was a valuable opportunity to bring together containerization, orchestration, persistent storage, monitoring, and UI development into a single cohesive system. It reinforced the challenges and rewards of building full-stack cloud applications and provided a deeper understanding of the end-to-end lifecycle—from local development to automated deployment in a managed Kubernetes environment.

