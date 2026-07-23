# Requirements Document

## Introduction

PROJECT_HIRE_DESK_AI is an intelligent web application that helps job seekers
organize, analyze, and track their job applications. The user pastes a job
description, Amazon Bedrock extracts structured information, the user reviews
and corrects the result, and the application is saved and tracked in a Kanban
board. A dashboard shows basic statistics and a next-action engine powered by
deterministic business rules guides the user through each application lifecycle.

The MVP targets a single demo user, uses a minimal serverless AWS architecture,
and must be completable in six days.

---

## Glossary

- **Application**: A job application record stored in DynamoDB, consisting of
  extracted and user-validated fields plus tracking metadata.
- **Bedrock_Client**: The backend Lambda component that calls Amazon Bedrock to
  analyze a job description and return structured extraction results.
- **Board**: The Kanban board view that displays all Applications organized by
  status column.
- **Dashboard**: The view that displays aggregate statistics about the user's
  Applications.
- **Extraction_Result**: The structured payload returned by the Bedrock_Client
  containing job title, company, location, required skills, responsibilities,
  languages, and experience level.
- **Job_Description**: Raw plain text pasted by the user representing a job
  posting.
- **Kanban_Column**: One status lane in the Board (e.g., Wishlist, Applied,
  Interview, Offer, Rejected).
- **Next_Action_Engine**: The deterministic backend component that computes the
  recommended next action for an Application based on status, dates, and
  business rules.
- **Next_Action_Recommendation**: The output of the Next_Action_Engine,
  consisting of an action label, a priority level, and an optional
  AI-generated explanation.
- **Status**: The current lifecycle stage of an Application, one of: Wishlist,
  Applied, Interview, Offer, Rejected.
- **User**: The single demo job-seeker using the application during the hackathon
  MVP phase.
- **Validator**: The frontend component that presents the Extraction_Result to
  the User for review and correction before saving.
- **API**: The Amazon API Gateway HTTP API that routes all requests between the
  frontend and the backend Lambda functions.
- **Lambda**: An AWS Lambda function written in Python that handles a specific
  backend operation.

---

## Requirements

### Requirement 1: Paste and Analyze a Job Description

**User Story:** As a User, I want to paste a job description and have the
system extract its key information automatically, so that I can avoid manual
data entry.

#### Acceptance Criteria

1. THE Validator SHALL provide a text input area that accepts plain text of up
   to 10 000 characters.
2. WHEN the User submits a Job_Description, THE API SHALL forward the
   Job_Description to the Bedrock_Client for analysis.
3. WHEN the Bedrock_Client receives a Job_Description, THE Bedrock_Client SHALL
   return an Extraction_Result containing at minimum: job title, company name,
   location, a list of required skills, a list of responsibilities, spoken or
   programming languages, and experience level; fields that cannot be extracted
   SHALL be returned as null.
4. WHEN the Bedrock_Client returns an Extraction_Result, THE Validator SHALL
   display all extracted fields to the User for review, rendering null fields as
   empty and editable, and SHALL NOT save any data until the User explicitly
   confirms the Application.
5. IF the Bedrock_Client fails to reach Amazon Bedrock or Amazon Bedrock returns
   an error, THEN THE API SHALL return an error response and THE Validator SHALL
   present the manual entry form so the User can enter application details
   without AI assistance.
6. IF Amazon Bedrock returns a response that does not conform to the expected
   Extraction_Result schema, THEN THE Bedrock_Client SHALL return a validation
   error and THE Validator SHALL present the manual entry form so the User can
   enter application details without AI assistance.
7. WHEN the Bedrock_Client sends a request to Amazon Bedrock, THE Bedrock_Client
   SHALL complete the request within 30 seconds.
8. IF the Bedrock_Client request to Amazon Bedrock exceeds 30 seconds, THEN THE
   Bedrock_Client SHALL cancel the request, return a timeout error, and THE
   Validator SHALL present the manual entry form.

---

### Requirement 2: Validate and Correct Extracted Information

**User Story:** As a User, I want to review and correct the extracted
information before saving, so that I can ensure the data is accurate.

#### Acceptance Criteria

1. THE Validator SHALL display each field of the Extraction_Result in an
   editable form.
2. WHEN the User modifies a field value, THE Validator SHALL update the local
   form state without saving to the backend.
3. THE Validator SHALL require the job title field to be non-empty before
   allowing the User to confirm the Application.
4. WHEN the User confirms the Application, THE Validator SHALL send the
   confirmed (and possibly corrected) data to the API for persistence.
5. IF the Lambda rejects the save request, THEN THE Validator SHALL display an
   error message describing the reason and SHALL keep the User on the
   confirmation form without clearing the entered data.
6. THE API SHALL accept a save request if and only if the request passes all
   Lambda validation checks; the API SHALL not apply additional validation rules
   beyond those enforced by the Lambda.
7. WHEN the Lambda receives a save request, THE Lambda SHALL validate that: the
   job title is non-empty; all string fields do not exceed 500 characters; all
   list items do not exceed 200 characters each; and no list contains more than
   30 items; and SHALL reject any request that contains DynamoDB table or index
   identifiers supplied by the client.
8. THE Validator SHALL keep the confirm action disabled until the job title field
   is non-empty and no field-level validation error is displayed in the form.

---

### Requirement 3: Create, Read, Update, and Delete Applications

**User Story:** As a User, I want to create, view, edit, and delete my job
applications, so that I can keep my records accurate and up to date.

#### Acceptance Criteria

1. WHEN the User confirms a new Application, THE Lambda SHALL write the
   Application to DynamoDB and return the generated application identifier.
2. WHEN the User requests the list of Applications, THE Lambda SHALL return all
   Applications belonging to the demo user, ordered by creation date descending;
   IF no Applications exist, THE Lambda SHALL return an empty list.
3. WHEN the User requests a single Application by identifier, THE Lambda SHALL
   return the full Application record if it exists.
4. IF the User requests a single Application by an identifier that does not
   exist, THEN THE Lambda SHALL return a not-found error.
5. WHEN the User updates an Application, THE Lambda SHALL persist only the
   provided fields to DynamoDB, preserve all other fields unchanged, and return
   the full updated Application record.
6. IF the User attempts to update an Application by an identifier that does not
   exist, THEN THE Lambda SHALL return a not-found error.
7. WHEN the User deletes an Application, THE Lambda SHALL remove the Application
   from DynamoDB and return a success response with no body.
8. IF the User attempts to delete an Application that does not exist, THEN THE
   Lambda SHALL return a not-found error.
9. WHEN the Lambda performs a DynamoDB read or write operation and the operation
   completes within 5 seconds, THE Lambda SHALL return the result to the caller.
10. IF a DynamoDB read or write operation does not complete within 5 seconds,
    THEN THE Lambda SHALL return a service-unavailable error and SHALL NOT
    partially persist any data from that operation.

---

### Requirement 4: Track Applications on a Kanban Board

**User Story:** As a User, I want to see all my applications organized by
status on a Kanban board, so that I can quickly understand where each
application stands.

#### Acceptance Criteria

1. THE Board SHALL display exactly five Kanban_Columns, one for each Status:
   Wishlist, Applied, Interview, Offer, and Rejected.
2. WHEN the User opens the Board, THE Board SHALL retrieve all Applications
   belonging to the demo user and display each Application card in the
   Kanban_Column that matches its Status.
3. IF no Applications exist for a Kanban_Column, THEN THE Board SHALL display
   the Kanban_Column as empty with a visible empty-state indicator.
4. WHEN the User moves an Application card to a different Kanban_Column, THE
   Board SHALL move the card in the UI within 500 ms and send a status-update
   request to the API.
5. IF the Lambda returns an error for a status-update request, THEN THE Board
   SHALL revert the Application card to its original Kanban_Column and display
   an error message describing the failure reason.
6. WHEN the API receives a status-update request with an invalid Status value,
   THE Lambda SHALL return a 400 error to the Board without updating DynamoDB.
7. WHEN the Status of an Application changes and the Lambda returns the updated
   Application record within 3 seconds, THE Next_Action_Engine SHALL recompute
   and persist the Next_Action_Recommendation before the Board performs its next
   retrieval.

---

### Requirement 5: Display Dashboard Statistics

**User Story:** As a User, I want to see summary statistics about my job
search on a dashboard, so that I can measure my progress and activity.

#### Acceptance Criteria

1. THE Dashboard SHALL display the total number of Applications.
2. THE Dashboard SHALL display the number of Applications for each of the five
   Status values: Wishlist, Applied, Interview, Offer, and Rejected.
3. THE Dashboard SHALL display the number of Applications whose creation date
   falls within the current calendar week, defined as Monday 00:00 UTC through
   Sunday 23:59 UTC.
4. WHEN the User opens the Dashboard, THE Lambda SHALL compute the statistics
   from the current state of all Applications in DynamoDB and return a single
   response containing: total count, per-status counts, and current-week count.
5. IF the Lambda fails to compute statistics due to a DynamoDB error, THEN THE
   Dashboard SHALL display an error message and SHALL NOT display any
   potentially stale statistic values.
6. WHEN an Application is created, updated, or deleted, THE Dashboard SHALL
   reflect the change the next time the User sends a statistics request.

---

### Requirement 6: Recommend the Next Action

**User Story:** As a User, I want the system to recommend what I should do
next for each application, so that I can focus my effort on the most important
actions.

#### Acceptance Criteria

1. THE Next_Action_Engine SHALL compute a Next_Action_Recommendation for each
   Application using only the Application's Status, creation date, last-updated
   date, and Status transition history.
2. WHEN an Application has Status Wishlist and was created more than 7 days ago
   without a Status change, THE Next_Action_Engine SHALL recommend the action
   "Apply now" with priority High.
3. WHEN an Application has Status Applied and was last updated more than 14 days
   ago without a Status change, THE Next_Action_Engine SHALL recommend the
   action "Follow up" with priority Medium.
4. IF an Application has Status Interview, THEN THE Next_Action_Engine SHALL
   recommend the action "Prepare for interview" with priority High.
5. IF an Application has Status Offer, THEN THE Next_Action_Engine SHALL
   recommend the action "Review and respond to offer" with priority High.
6. IF an Application has Status Rejected, THEN THE Next_Action_Engine SHALL
   recommend the action "Archive or reapply" with priority Low.
7. WHERE the Amazon Bedrock integration is available, THE Bedrock_Client SHALL
   generate a personalized explanation not exceeding 280 characters, derived
   from the Application's Status and Status transition history, and attach it to
   the Next_Action_Recommendation.
8. IF the Amazon Bedrock integration is unavailable due to a failed connection,
   timeout, or error response from the Bedrock service, THEN THE
   Next_Action_Engine SHALL return the Next_Action_Recommendation without an
   AI-generated explanation.
9. THE Next_Action_Engine SHALL determine action labels and priorities using
   only deterministic business rules, independent of any AI-generated content.
10. IF an Application has a Status that is not covered by criteria 2–6, THEN THE
    Next_Action_Engine SHALL return no recommendation for that Application.
11. IF an Application has Status Wishlist and was created 7 days ago or less
    without a Status change, THEN THE Next_Action_Engine SHALL return no
    recommendation for that Application; IF an Application has Status Applied
    and was last updated 14 days ago or less without a Status change, THEN THE
    Next_Action_Engine SHALL return no recommendation for that Application.

---

### Requirement 7: Frontend Routing and Navigation

**User Story:** As a User, I want to navigate between the Kanban board, the
dashboard, and the job-description entry form without page reloads, so that
the application feels responsive.

#### Acceptance Criteria

1. THE Frontend SHALL provide exactly three distinct routes: /board for the
   Board view, /dashboard for the Dashboard view, and /new for the new
   Application entry form.
2. WHEN the User navigates to a route, THE Frontend SHALL render the
   corresponding view within 300 ms without a full page reload.
3. THE Frontend SHALL display a persistent navigation bar on every route that
   contains a link to each of the three routes.
4. THE Frontend SHALL highlight the navigation bar link that corresponds to the
   currently active route.
5. IF the User navigates to a route that is not /board, /dashboard, or /new,
   THEN THE Frontend SHALL redirect the User to the /board route.

---

### Requirement 8: API Security and Input Validation

**User Story:** As a system operator, I want all API inputs to be validated
and all AWS credentials to remain server-side, so that the application is not
exposed to injection attacks or credential leaks.

#### Acceptance Criteria

1. THE Frontend SHALL never include AWS credentials, DynamoDB identifiers, or
   Amazon Bedrock endpoint details in any outbound network request.
2. WHEN the Lambda receives an incoming request, THE Lambda SHALL validate the
   type, format, and length of every field — strings not exceeding 1,000
   characters, lists not exceeding 100 items, and numeric fields within their
   defined domain range — and SHALL reject any request that contains DynamoDB
   table or index identifiers supplied by the client, without processing the
   request.
3. IF a request contains a field that fails validation, THEN THE Lambda SHALL
   return a 400 error with a message describing which field failed and why,
   without processing or persisting any part of the request.
4. IF the API receives a request with a payload larger than 20 KB, THEN THE API
   SHALL return a 413 error without processing the request body.
5. WHEN the Lambda encounters an error, THE Lambda SHALL log the error to Amazon
   CloudWatch including the request identifier, the error type, and a
   description that contains no raw user-supplied input values or credential
   data.

---

### Requirement 9: Infrastructure Reproducibility

**User Story:** As a developer, I want the entire AWS infrastructure to be
defined in a single SAM template, so that the environment can be recreated
from scratch in one command.

#### Acceptance Criteria

1. THE Infrastructure SHALL define all Lambda functions, the API, and the
   DynamoDB table in a single `template.yaml` AWS SAM file, and no AWS resource
   required for system operation SHALL be defined outside that file.
2. THE Infrastructure SHALL not reference any S3 buckets, SES resources, or
   EventBridge rules.
3. WHEN a developer runs `sam deploy`, THE Infrastructure SHALL provision all
   required AWS resources without requiring manual console steps.
4. IF any resource fails to provision during `sam deploy`, THEN THE
   Infrastructure SHALL perform a complete rollback leaving no partially-created
   resources in the AWS account.
5. THE Infrastructure SHALL define the DynamoDB table with on-demand (PAY_PER_REQUEST)
   capacity mode.
6. WHEN `sam deploy` completes successfully, THE CLI output SHALL include the
   API Gateway endpoint URL so the developer can verify the deployment without
   accessing the AWS console.
