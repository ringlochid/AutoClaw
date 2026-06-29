# MVP build workflow example

Status: Reference

This example mirrors the shipped `mvp-build` workflow fixture.

```yaml
kind: workflow
id: mvp-build
description: Discover the core value, build a thin usable slice, verify the demo path, review product fit, and close with release evidence.
root:
    id: root
    role: root_planning_lead
    policy: standard-root-planning
    description: Preserve MVP scope and release only when the thin slice proves the intended value with current review and verification evidence.
    instruction: >-
      Keep MVP work thin. Route non-core polish, broad platform work, and speculative
      expansion to follow-up scope.
    criteria:
        - slot: mvp_release_criteria
          description: Hard criteria for MVP release.
          criteria:
              - MVP scope names the target user, core job, thin-slice behavior, and explicit deferrals
              - implementation, demo verification, code review, and product review refer to the same MVP scope
              - unresolved core-value or high-risk technical issues block release
    children:
        - id: discover_mvp_value
          role: product_planner
          policy: standard-product-planning
          description: Define the MVP user value, thin slice, deferrals, and acceptance criteria.
          instruction: >-
            Keep the scope focused on the smallest usable proof of value.
          produces:
              artifacts:
                  - slot: mvp_scope
                    file_hint: mvp_scope.md
                    description: MVP target user, core value, thin-slice scope, deferrals, and acceptance criteria.
        - id: implement_mvp_slice
          role: engineer
          policy: standard-worker
          description: Implement the thin MVP slice from accepted scope.
          instruction: >-
            Build only the accepted MVP slice. Defer polish and broad infrastructure
            unless criteria require it.
          consumes:
              artifacts:
                  - slot: mvp_scope
          criteria:
              - slot: mvp_implementation_criteria
                description: Hard implementation criteria for the MVP slice.
                criteria:
                    - patch implements the accepted thin slice without expanding into deferred scope
                    - checkpoint names changed areas, evidence read, verification attempted, and residual risk
          produces:
              artifacts:
                  - slot: mvp_patch
                    file_hint: mvp_patch.diff
                    description: Patch for the MVP thin slice.
        - id: verify_demo_path
          role: test_verifier
          policy: standard-long-command-worker
          description: Verify the MVP demo path and core acceptance behavior.
          instruction: >-
            Verify the smallest user path that proves MVP value and name untested
            follow-up areas.
          consumes:
              artifacts:
                  - slot: mvp_scope
                  - slot: mvp_patch
              criteria:
                  - slot: mvp_implementation_criteria
          produces:
              artifacts:
                  - slot: demo_verification_report
                    file_hint: demo_verification_report.md
                    description: Verification evidence for the MVP demo path.
        - id: review_mvp_code
          role: code_reviewer
          policy: standard-review
          description: Review the MVP patch and demo verification evidence.
          instruction: >-
            Focus on correctness, regression risk, missing tests, and whether the patch
            stayed inside MVP scope.
          consumes:
              artifacts:
                  - slot: mvp_scope
                  - slot: mvp_patch
                  - slot: demo_verification_report
              criteria:
                  - slot: mvp_release_criteria
          produces:
              artifacts:
                  - slot: mvp_code_review
                    file_hint: mvp_code_review.md
                    description: Code review findings for the MVP slice.
        - id: review_product_fit
          role: product_reviewer
          policy: standard-scope-review
          description: Review whether the MVP slice proves the intended product value.
          instruction: >-
            Judge user value, deferrals, acceptance gaps, and whether the next workflow
            should build, revise, or stop.
          consumes:
              artifacts:
                  - slot: mvp_scope
                  - slot: demo_verification_report
                  - slot: mvp_code_review
              criteria:
                  - slot: mvp_release_criteria
          produces:
              artifacts:
                  - slot: product_fit_review
                    file_hint: product_fit_review.md
                    description: Product-fit review for the MVP slice.
        - id: release_closure
          role: release_operator
          policy: standard-release
          description: Perform final bounded MVP release or closure work from current surfaced evidence.
          instruction: >-
            Use only MVP scope, patch, verification, code review, product review, and
            release criteria.
          consumes:
              artifacts:
                  - slot: mvp_scope
                  - slot: mvp_patch
                  - slot: demo_verification_report
                  - slot: mvp_code_review
                  - slot: product_fit_review
              criteria:
                  - slot: mvp_release_criteria
          produces:
              artifacts:
                  - slot: closure_report
                    file_hint: closure_report.md
                    description: Final MVP release or closure report.
```
