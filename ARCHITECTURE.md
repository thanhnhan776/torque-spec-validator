# Proposed AWS deployment

This is a deployment sketch, not functionality implemented in the current app.

## Components

```text
Browser ── CloudFront / S3 (React)
   │
   ├── API Gateway ── FastAPI on ECS/Fargate ── DynamoDB (jobs / results)
   │                         │
   └── presigned multipart ──► S3 uploads ── SQS ── ECS/Fargate workers
                                                     │
                                             S3 results / DynamoDB
```

1. Authenticate users and authorize each job. The API creates a job and short-lived presigned S3 multipart upload URLs. The browser uploads parts directly to S3, retries failed parts, then completes the upload. Configure bucket CORS for the frontend and lifecycle cleanup for abandoned multipart uploads.
2. An S3 object-created event sends the completed upload to SQS. A worker claims the job, inspects the ZIP and validates its XML files, recording per-file status and results. Workers can scale with queue backlog; an initial implementation may process the 200+ files sequentially inside a job and add per-file fan-out if throughput requires it.
3. The UI polls a short job-status API request, displaying progress and partial failures. Store metadata and status in DynamoDB; store large result payloads and CSV exports in S3 rather than database items. Retain the original upload only according to a defined retention policy.

## Large uploads and timeouts

The 500 MB ZIP never passes through API Gateway. The API only initiates the upload and returns job status; validation is asynchronous, so it does not wait for the assignment's 29-second API Gateway timeout. API Gateway quotas vary by API type; this design avoids depending on a longer timeout.

## Reliability and security

- S3 notifications and standard SQS delivery can be repeated: use idempotent job/file identifiers and conditional state updates. Set an appropriate visibility timeout, extend it for long jobs, and use retries and a dead-letter queue.
- Treat ZIP and XML as untrusted: reject path traversal and unsafe links, cap file count, expanded size and compression ratio, and disable unsafe XML features. Scan uploads as required; checksums verify integrity, not safety.
- Use private buckets, encryption, least-privilege IAM, authenticated per-user access, short-lived URLs, and access logging. Monitor queue age, failures, worker capacity, processing time and storage; define alerting and retention.

## References

- [S3 multipart upload](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)
- [S3 event notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html)
- [SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- [API Gateway HTTP API quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html)
