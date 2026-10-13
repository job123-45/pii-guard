# Solution blueprint

```mermaid
flowchart LR
 U[User uploads] --> V[File validation]
 V --> E[Format-specific extraction]
 E --> S[Normalized source segments]
 S --> D[Layered PII detection]
 D --> R[Span-based text redaction]
 R --> H{Fail-closed privacy gateway}
 H -->|Allow| L[Simulated downstream AI]
 H -->|Block| Q[Human review]
 D --> A[Traceable audit report]
```

The gateway permits only complete, validated, review-free sanitized text. Uncertain extraction, OCR/image content needing review, validation failure or unresolved low-confidence findings blocks release. The interface labels exports as sanitized text, never as redacted original files.
