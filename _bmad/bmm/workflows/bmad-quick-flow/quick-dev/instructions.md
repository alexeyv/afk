# Quick-Dev - Flexible Development Workflow

<workflow>

<critical>Communicate in {communication_language}, tailored to {user_skill_level}</critical>
<critical>Execute continuously until COMPLETE - do not stop for milestones</critical>
<critical>Flexible - handles tech-specs OR direct instructions</critical>
<critical>ALWAYS respect {project_context} if it exists - it defines project standards</critical>

<checkpoint-handlers>
  <on-select key="a">Load and execute {advanced_elicitation}, then return</on-select>
  <on-select key="p">Load and execute {party_mode_workflow}, then return</on-select>
  <on-select key="t">Load and execute {create_tech_spec_workflow}</on-select>
</checkpoint-handlers>

<step n="1" goal="Load project context and determine execution mode">

<action>Check if {project_context} exists. If yes, load it - this is your foundational reference for ALL implementation decisions (patterns, conventions, architecture).</action>

<action>Parse user input:

**Mode A: Tech-Spec** - e.g., `quick-dev tech-spec-auth.md`
→ Load spec, extract tasks/context/AC, goto step 3

**Mode B: Direct Instructions** - e.g., `refactor src/foo.ts...`
→ Offer planning choice
</action>

<check if="Mode A">
  <action>Load tech-spec, extract tasks/context/AC</action>
  <goto>step_3</goto>
</check>

<check if="Mode B">

  <!-- Escalation Threshold: Lightweight check - should we invoke scale-adaptive? -->

<action>Evaluate escalation threshold against user input (minimal tokens, no file loading):

**Triggers escalation** (if 2+ signals present):

- Multiple components mentioned (e.g., dashboard + api + database)
- System-level language (e.g., platform, integration, architecture)
- Uncertainty about approach (e.g., "how should I", "best way to")
- Multi-layer scope (e.g., UI + backend + data together)
- Extended timeframe (e.g., "this week", "over the next few days")

**Reduces signal:**

- Simplicity markers (e.g., "just", "quickly", "fix", "bug", "typo", "simple", "basic", "minor")
- Single file/component focus
- Confident, specific request

Use holistic judgment, not mechanical keyword matching.</action>

  <!-- No Escalation: Simple request, offer existing choice -->
  <check if="escalation threshold NOT triggered">
    <ask>**[t] Plan first** - Create tech-spec then implement
**[e] Execute directly** - Start now</ask>

    <check if="t">
      <action>Load and execute {create_tech_spec_workflow}</action>
      <action>Continue to implementation after spec complete</action>
    </check>

    <check if="e">
      <ask>Any additional guidance before I begin? (patterns, files, constraints) Or "go" to start.</ask>
      <goto>step_2</goto>
    </check>

  </check>

  <!-- Escalation Triggered: Load scale-adaptive and evaluate level -->
  <check if="escalation threshold triggered">
    <action>Load {project_levels} and evaluate user input against detection_hints.keywords</action>
    <action>Determine level (0-4) using scale-adaptive definitions</action>

    <!-- Level 0: Scale-adaptive confirms simple, fall back to standard choice -->
    <check if="level 0">
      <ask>**[t] Plan first** - Create tech-spec then implement

**[e] Execute directly** - Start now</ask>

      <check if="t">
        <action>Load and execute {create_tech_spec_workflow}</action>
        <action>Continue to implementation after spec complete</action>
      </check>

      <check if="e">
        <ask>Any additional guidance before I begin? (patterns, files, constraints) Or "go" to start.</ask>
        <goto>step_2</goto>
      </check>
    </check>

    <check if="level 1 or 2 or couldn't determine level">
      <ask>This looks like a focused feature with multiple components.

**[t] Create tech-spec first** (recommended)
**[w] Seems bigger than quick-dev** — see what BMad Method recommends (workflow-init)
**[e] Execute directly**</ask>

      <check if="t">
        <action>Load and execute {create_tech_spec_workflow}</action>
        <action>Continue to implementation after spec complete</action>
      </check>

      <check if="w">
        <action>Load and execute {workflow_init}</action>
        <action>EXIT quick-dev - user has been routed to BMad Method</action>
      </check>

      <check if="e">
        <ask>Any additional guidance before I begin? (patterns, files, constraints) Or "go" to start.</ask>
        <goto>step_2</goto>
      </check>
    </check>

    <!-- Level 3+: BMad Method territory, recommend workflow-init -->
    <check if="level 3 or higher">
      <ask>This sounds like platform/system work.

**[w] Start BMad Method** (recommended) (workflow-init)
**[t] Create tech-spec** (lighter planning)
**[e] Execute directly** - feeling lucky</ask>

      <check if="w">
        <action>Load and execute {workflow_init}</action>
        <action>EXIT quick-dev - user has been routed to BMad Method</action>
      </check>

      <check if="t">
        <action>Load and execute {create_tech_spec_workflow}</action>
        <action>Continue to implementation after spec complete</action>
      </check>

      <check if="e">
        <ask>Any additional guidance before I begin? (patterns, files, constraints) Or "go" to start.</ask>
        <goto>step_2</goto>
      </check>
    </check>

  </check>

</check>

</step>

<step n="2" goal="Quick context gathering (direct mode)">

<action>Identify files to modify, find relevant patterns, note dependencies</action>

<action>Create mental plan: tasks, acceptance criteria, files to touch</action>

</step>

<step n="3" goal="Execute implementation" id="step_3">

<action>For each task:

1. **Load Context** - read files from spec or relevant to change
2. **Implement** - follow patterns, handle errors, follow conventions
3. **Test** - write tests, run existing tests, verify AC
4. **Mark Complete** - check off task [x], continue
   </action>

<action if="3 failures">HALT and request guidance</action>
<action if="tests fail">Fix before continuing</action>

<critical>Continue through ALL tasks without stopping</critical>

</step>

<step n="4" goal="Verify and transition to review">

<action>Verify: all tasks [x], tests passing, AC satisfied, patterns followed</action>

<check if="using tech-spec">
  <action>Update tech-spec status to "Completed", mark all tasks [x]</action>
</check>

<output>**Implementation Complete!**

**Summary:** {{implementation_summary}}
**Files Modified:** {{files_list}}
**Tests:** {{test_summary}}
**AC Status:** {{ac_status}}

Running adversarial code review...
</output>

<action>Proceed immediately to step 5 - NO USER PROMPT</action>

</step>

<step n="5" goal="Adversarial code review (automatic)">

<!-- EXECUTE AUTOMATICALLY - No user prompt until findings are ready -->

<action>Construct diff of implementation changes:
  - Uncommitted changes: `git diff` + `git diff --cached`
  - Set {{review_target}} = combined diff output
</action>

<!-- Execution hierarchy: cleanest context first -->
<check if="can spawn subagent (Task tool available)">
  <action>Launch subagent to conduct adversarial code review of {{review_target}}</action>
  <action>Subagent prompt: "Review this diff as a cynical, skeptical code reviewer. Find at least 5-10 issues - bugs, missing error handling, security concerns, performance issues, style problems. Be suspicious of everything. Number each finding."</action>
</check>

<check if="no subagent BUT can invoke separate CLI process">
  <action>Execute adversarial review via CLI (`claude --print`) in fresh context</action>
</check>

<check if="inline fallback (no subagent, no CLI)">
  <action>Conduct adversarial review inline. Prompt self: "Switch to cynical reviewer mode. Find at least 10 issues in this diff. Number them. Be skeptical."</action>
</check>

<action>Collect numbered findings into {{review_findings}}</action>

<!-- SANITY CHECK: Review should NEVER return empty -->
<check if="{{review_findings}} is empty or contains no numbered items">
  <output>**⚠️ ADVERSARIAL REVIEW FAILED**

🚨 Zero findings returned. This should never happen - the review is designed to always find something.

Run `/bmad:bmm:workflows:code-review` manually.
  </output>
  <action>HALT</action>
</check>

<action>Process each finding:
  1. Assign ID: F1, F2, F3...
  2. Assign severity: 🔴 (critical) 🟠 (significant) 🟡 (minor) 🟢 (trivial)
  3. Classify: "real", "noise", or uncertainty type with "?" (e.g., "style?", "context?")
  4. Sort by severity (🔴 first)
</action>

<output>**🔥 ADVERSARIAL CODE REVIEW FINDINGS**

| ID | Finding | | Class |
|----|---------|:-:|-------|
{{findings_table}}

**Summary:** {{real_count}} real, {{uncertain_count}} uncertain, {{noise_count}} noise
</output>

<action>Create a todo for each finding (F1, F2, F3...)</action>

<ask>How would you like to handle these findings?

1. **Walk through together** - Go through each finding one by one (recommended)
2. **Auto-fix real issues** - Fix all "real" 🔴/🟠 findings automatically
3. **Skip all** - Proceed without changes

Choose [1], [2], or [3]:</ask>

<check if="user chooses 1 (walk through)">
  <action>For each finding in severity order:
    1. Mark todo in-progress
    2. Explain: what, where, why it matters, suggested fix
    3. Ask: fix / skip / discuss
    4. Handle response, mark todo completed
    5. Next finding
  </action>
</check>

<check if="user chooses 2 (auto-fix)">
  <action>Fix all "real" 🔴/🟠 findings automatically</action>
  <action>Run tests to verify fixes don't break anything</action>
  <action>Mark todos completed</action>
</check>

<check if="user chooses 3 (skip)">
  <action>Mark all todos completed (skipped)</action>
</check>

<output>**Review complete.** Ready to commit.</output>

<action>Explain what was implemented based on {user_skill_level}</action>

</step>

</workflow>
