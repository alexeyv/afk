# BMM Workflows

## Available Workflows in bmm

**create-product-brief**
- Path: `.bmad/bmm/workflows/1-analysis/product-brief/workflow.md`
- Create comprehensive product briefs through collaborative step-by-step discovery as creative Business Analyst working with the user as peers.

**research**
- Path: `.bmad/bmm/workflows/1-analysis/research/workflow.md`
- Conduct comprehensive research across multiple domains using current web data and verified sources - Market, Technical, Domain and other research types.

**create-ux-design**
- Path: `.bmad/bmm/workflows/2-plan-workflows/create-ux-design/workflow.md`
- Work with a peer UX Design expert to plan your applications UX patterns, look and feel.

**create-prd**
- Path: `.bmad/bmm/workflows/2-plan-workflows/prd/workflow.md`
- Creates a comprehensive PRDs through collaborative step-by-step discovery between two product managers working as peers.

**create-architecture**
- Path: `.bmad/bmm/workflows/3-solutioning/architecture/workflow.md`
- Collaborative architectural decision facilitation for AI-agent consistency. Replaces template-driven architecture with intelligent, adaptive conversation that produces a decision-focused architecture document optimized for preventing agent conflicts.

**create-epics-stories**
- Path: `.bmad/bmm/workflows/3-solutioning/create-epics-and-stories/workflow.md`
- Transform PRD requirements and Architecture decisions into comprehensive stories organized by user value. This workflow requires completed PRD + Architecture documents (UX recommended if UI exists) and breaks down requirements into implementation-ready epics and user stories that incorporate all available technical and design context. Creates detailed, actionable stories with complete acceptance criteria for development teams.

**check-implementation-readiness**
- Path: `.bmad/bmm/workflows/3-solutioning/implementation-readiness/workflow.md`
- Critical validation workflow that assesses PRD, Architecture, and Epics & Stories for completeness and alignment before implementation. Uses adversarial review approach to find gaps and issues.

**code-review**
- Path: `.bmad/bmm/workflows/4-implementation/code-review/workflow.yaml`
- Perform an ADVERSARIAL Senior Developer code review that finds 3-10 specific problems in every story. Challenges everything: code quality, test coverage, architecture compliance, security, performance. NEVER accepts `looks good` - must find minimum issues and can auto-fix with user approval.

**correct-course**
- Path: `.bmad/bmm/workflows/4-implementation/correct-course/workflow.yaml`
- Navigate significant changes during sprint execution by analyzing impact, proposing solutions, and routing for implementation

**create-story**
- Path: `.bmad/bmm/workflows/4-implementation/create-story/workflow.yaml`
- Create the next user story from epics+stories with enhanced context analysis and direct ready-for-dev marking

**dev-story**
- Path: `.bmad/bmm/workflows/4-implementation/dev-story/workflow.yaml`
- Execute a story by implementing tasks/subtasks, writing tests, validating, and updating the story file per acceptance criteria

**retrospective**
- Path: `.bmad/bmm/workflows/4-implementation/retrospective/workflow.yaml`
- Run after epic completion to review overall success, extract lessons learned, and explore if new information emerged that might impact the next epic

**sprint-planning**
- Path: `.bmad/bmm/workflows/4-implementation/sprint-planning/workflow.yaml`
- Generate and manage the sprint status tracking file for Phase 4 implementation, extracting all epics and stories from epic files and tracking their status through the development lifecycle

**sprint-status**
- Path: `.bmad/bmm/workflows/4-implementation/sprint-status/workflow.yaml`
- Summarize sprint-status.yaml, surface risks, and route to the right implementation workflow.

**create-tech-spec**
- Path: `.bmad/bmm/workflows/bmad-quick-flow/create-tech-spec/workflow.yaml`
- Conversational spec engineering - ask questions, investigate code, produce implementation-ready tech-spec.

**quick-dev**
- Path: `.bmad/bmm/workflows/bmad-quick-flow/quick-dev/workflow.yaml`
- Flexible development - execute tech-specs OR direct instructions with optional planning.

**create-excalidraw-dataflow**
- Path: `.bmad/bmm/workflows/diagrams/create-dataflow/workflow.yaml`
- Create data flow diagrams (DFD) in Excalidraw format

**create-excalidraw-diagram**
- Path: `.bmad/bmm/workflows/diagrams/create-diagram/workflow.yaml`
- Create system architecture diagrams, ERDs, UML diagrams, or general technical diagrams in Excalidraw format

**create-excalidraw-flowchart**
- Path: `.bmad/bmm/workflows/diagrams/create-flowchart/workflow.yaml`
- Create a flowchart visualization in Excalidraw format for processes, pipelines, or logic flows

**create-excalidraw-wireframe**
- Path: `.bmad/bmm/workflows/diagrams/create-wireframe/workflow.yaml`
- Create website or app wireframes in Excalidraw format

**document-project**
- Path: `.bmad/bmm/workflows/document-project/workflow.yaml`
- Analyzes and documents brownfield projects by scanning codebase, architecture, and patterns to create comprehensive reference documentation for AI-assisted development

**generate-project-context**
- Path: `.bmad/bmm/workflows/generate-project-context/workflow.md`
- Creates a concise project_context.md file with critical rules and patterns that AI agents must follow when implementing code. Optimized for LLM context efficiency.

**testarch-atdd**
- Path: `.bmad/bmm/workflows/testarch/atdd/workflow.yaml`
- Generate failing acceptance tests before implementation using TDD red-green-refactor cycle

**testarch-automate**
- Path: `.bmad/bmm/workflows/testarch/automate/workflow.yaml`
- Expand test automation coverage after implementation or analyze existing codebase to generate comprehensive test suite

**testarch-ci**
- Path: `.bmad/bmm/workflows/testarch/ci/workflow.yaml`
- Scaffold CI/CD quality pipeline with test execution, burn-in loops, and artifact collection

**testarch-framework**
- Path: `.bmad/bmm/workflows/testarch/framework/workflow.yaml`
- Initialize production-ready test framework architecture (Playwright or Cypress) with fixtures, helpers, and configuration

**testarch-nfr**
- Path: `.bmad/bmm/workflows/testarch/nfr-assess/workflow.yaml`
- Assess non-functional requirements (performance, security, reliability, maintainability) before release with evidence-based validation

**testarch-test-design**
- Path: `.bmad/bmm/workflows/testarch/test-design/workflow.yaml`
- Dual-mode workflow: (1) System-level testability review in Solutioning phase, or (2) Epic-level test planning in Implementation phase. Auto-detects mode based on project phase.

**testarch-test-review**
- Path: `.bmad/bmm/workflows/testarch/test-review/workflow.yaml`
- Review test quality using comprehensive knowledge base and best practices validation

**testarch-trace**
- Path: `.bmad/bmm/workflows/testarch/trace/workflow.yaml`
- Generate requirements-to-tests traceability matrix, analyze coverage, and make quality gate decision (PASS/CONCERNS/FAIL/WAIVED)

**workflow-init**
- Path: `.bmad/bmm/workflows/workflow-status/init/workflow.yaml`
- Initialize a new BMM project by determining level, type, and creating workflow path

**workflow-status**
- Path: `.bmad/bmm/workflows/workflow-status/workflow.yaml`
- Lightweight status checker - answers "what should I do now?" for any agent. Reads YAML status file for workflow tracking. Use workflow-init for new projects.


## Execution

When running any workflow:
1. LOAD {project-root}/.bmad/core/tasks/workflow.xml
2. Pass the workflow path as 'workflow-config' parameter
3. Follow workflow.xml instructions EXACTLY
4. Save outputs after EACH section

## Modes
- Normal: Full interaction
- #yolo: Skip optional steps
