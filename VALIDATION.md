# Validation results

Executed locally on 15 October 2026:

- PASS: five Python unit tests, including normalized duplicates, threshold boundary, invalid monetary inputs, invalid payload types and 20 concurrent duplicate requests.
- NOT VERIFIED: HTTP smoke test. The sandbox blocked the loopback client connection with Windows error 10013.
- NOT VERIFIED: Docker build. Docker CLI exists, but access to its buildx lock under the user profile was denied.
- NOT VERIFIED: Terraform formatting, initialization and provider validation. Terraform is not installed; downloading the binary failed due to DNS/network restrictions. The included GitHub Actions job runs formatting and validation when uploaded.
- NOT VERIFIED: PostgreSQL integration, GitHub Actions execution and AWS deployment. No AWS resources were created.

Run the README commands in your normal terminal to complete integration verification. Review provider plans before deployment; this project must not be described as production-validated.

## Dashboard update — 15 October 2026

- PASS: existing five Python tests rerun.
- PASS: live browser loaded dashboard from Python server at http://localhost:8080/.
- PASS: invoice submission displayed high-amount review; resubmission displayed duplicate-reference review; a new 120.00 invoice displayed low risk.
- PASS: session counts and recent assessments updated; Load example populated the invoice form.
- Visual layout inspected at the in-app browser's narrow viewport.

The earlier HTTP restriction was overcome by running the preview server with authorized host access. Terraform, Docker and PostgreSQL integration remain unverified as described above.
