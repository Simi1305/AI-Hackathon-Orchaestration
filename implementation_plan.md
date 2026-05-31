# Role-Based Feature Integration Plan

This plan details how the backend APIs and frontend integrations will be built to fulfill the comprehensive role-based features requested, without altering any UI layouts or visual styling.

## Verification of UI Freeze constraint
As explicitly requested, the UI is completely frozen. 
- No CSS files or inline styling classes will be altered.
- The structure of the React components (grids, divs, flex containers) will remain intact.
- Functionality will be injected into the existing placeholder cards and layouts. If a new piece of data needs to be displayed, it will be injected into an existing structural element in a way that respects the current layout.
- We will NOT rip apart your `App.jsx` into an entirely different design system like the previous agent did.

## Proposed Changes

### 1. Backend API Expansion
To support the feature-rich dashboards, we will utilize the existing backend models (which already contain `UserRole`, `Team`, `Score`, `ParticipantProfile`, etc.) and expose missing endpoints in `main.py` and `schemas.py`.

#### Participant API
- `GET /api/v1/participant/me`: Returns profile (institution, skills, experience, team synergy score) and assigned mentor.
- `GET /api/v1/teams/{team_id}`: Returns teammate details.
- `POST /api/v1/teams/{team_id}/submit`: Endpoint to upload project presentation/github links.

#### Mentor API
- `GET /api/v1/mentor/me`: Returns assigned teams, project domains, and submission status.
- `POST /api/v1/teams/{team_id}/feedback`: Submits mentor notes/feedback.

#### Judge API
- `GET /api/v1/judge/me`: Returns evaluation queue and completed reviews.
- `POST /api/v1/submit-score`: Submits rubric evaluation (already partially implemented, needs mapping to judge profile).

#### Organizer API
- `GET /api/v1/dashboard/full-analytics`: Returns metrics for the master control center charts.
- `GET /api/v1/users`: Manages users (Participants, Mentors, Judges).
- `POST /api/v1/trigger-team-formation`: Triggers deterministic team formation.

---

### 2. Frontend Integration (`frontend/src/App.jsx`)

Instead of replacing the UI, we will inject state and conditional rendering based on the logged-in role into your existing `App.jsx`.

#### [MODIFY] [App.jsx](file:///c:/Users/sahas/ti/AI-Hackathon-Orchaestration/frontend/src/App.jsx)
1. **Auth State & Routing:** Add a simple Login View (matching the dark theme style) at the root level, or use a dropdown to "Switch Role" for testing purposes. Upon selecting a role, `App.jsx` will set a `role` state (`PARTICIPANT`, `MENTOR`, `JUDGE`, `ORGANIZER`).
2. **Role-Based Sidebar Navigation:** Update the `navItems` array to dynamically filter which sidebar buttons appear based on the active `role`.
3. **Data Fetching (useEffect hooks):** 
   - Add API calls in `useEffect` blocks to fetch dashboard analytics.
   - Replace hardcoded static data inside the `HeroCard`, `LineChart`, and `Insight` UI blocks with the data pulled from `fetch()`.
4. **Role-Based Views:**
   - **Organizer:** Renders the master control charts, approval center tables, and team formation controls using the existing grid layout.
   - **Participant:** Renders the Profile, Team details, and Submission upload form using existing card layouts.
   - **Mentor/Judge:** Renders the Evaluation Queue and Feedback tables utilizing the existing table UI structures found in the file.

### 3. Cleanup
- Remove dead routes and broken buttons.
- Deduplicate hardcoded UI cards by mapping over real backend arrays.

## Open Questions
> [!WARNING]
> Since we are strictly maintaining the single-file `App.jsx` structure to preserve your UI, the file will grow significantly larger as we add API hooks and logic for 4 different roles. Is it acceptable to split the logic into smaller files inside `frontend/src/pages/` **AS LONG AS** the exact CSS and HTML structure is identically preserved? If you prefer everything to remain inside `App.jsx`, I will happily do it all in one file!

## Verification Plan

### Automated Tests
- I will write a Python script `verify_api.py` to test the backend endpoints for all 4 roles.

### Manual Verification
- I will run `npm run dev` and `uvicorn main:app --reload` to ensure the live platform renders without errors and accurately serves role-specific data.
