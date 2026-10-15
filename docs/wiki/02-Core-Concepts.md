# Core Concepts

## The CEPIO operating model

CEPIO combines three dimensions:

```text
                           CEPIO
                             |
          +------------------+------------------+
          |                  |                  |
      SEMANTICS            STATE             KINETICS
          |                  |                  |
      Objects              Events             Functions
      Relationships        Time               Decisions
      Properties           History            Actions
      Interfaces           Provenance         Workflows
      Capabilities         Projection         Constraints
          |                  |                  |
          +------------------+------------------+
                             |
                      Policy + Audit
```

## Object

An **Object** represents a durable thing the enterprise cares about.

Examples:

- compressor;
- process unit;
- well;
- rig;
- work order;
- supplier;
- contract;
- organization;
- project;
- material;
- KPI;
- risk.

Objects have stable CEPIO identity even if identifiers in source systems change.

## Relationship

A **Relationship** connects objects using typed industrial semantics.

Examples:

```text
Compressor --installedIn--> Hydrocracker
Compressor --hasWorkOrder--> WorkOrder
Pump --drivenBy--> Motor
ProcessUnit --produces--> Product
WorkOrder --requires--> SparePart
Supplier --supplies--> SparePart
```

Relationships may also carry temporal history.

## Property

A **Property** is a typed attribute with canonical meaning.

Properties are not simply copied source columns. Each source field is classified into the canonical property contract, an observation, a relationship key, provenance metadata or a customer-specific extension.

## Event

An **Event** is an immutable occurrence.

Examples:

- trip;
- start;
- shutdown;
- inspection;
- anomaly detection;
- work-order completion;
- material receipt;
- approval;
- action execution.

Events can be used to deterministically derive operational state.

## State

**State** is the current or historical condition of an object derived from authoritative facts and/or events.

Example:

```text
TripEvent
   -> CompressorOperatingStateProjector
   -> operatingState = "tripped"

RecoveryEvent
   -> projector
   -> operatingState = "running"
```

## Function

A **Function** performs typed calculation, reasoning or transformation without being treated as an externally consequential action.

Examples:

- calculate production-loss exposure;
- estimate equipment risk;
- compute remaining margin opportunity;
- identify blast radius;
- recommend maintenance priority.

## Decision

A **Decision** records the evidence, logic and conclusion connecting observed state to a recommended course of action.

Decision records are useful because industrial AI should be able to explain not only *what* it recommends, but *why*.

## Action

An **Action** represents a governed operation that changes CEPIO state or invokes an enterprise side effect.

Examples:

- create SAP work order;
- approve inspection plan;
- reschedule a task;
- issue procurement request;
- publish an operating recommendation;
- execute an authorized external workflow.

Actions are subject to authorization, policy, preconditions, idempotency and audit.

## Policy

**Policy** determines what an actor may read, reason over, recommend and execute.

The actor can be a human, application, service identity or AI agent.

## Provenance

**Provenance** explains how CEPIO arrived at a fact or property value.

Typical provenance elements include:

- source system;
- source entity;
- source field;
- source record;
- source-value hash;
- mapping version;
- transformation run;
- observed time;
- ingestion time.

## Profile

A **Profile** specializes canonical CEPIO semantics for a customer, asset, site or use case without redefining the universal core.

Examples in the repository include profile directions for SATORP/SEO and ARO/AD.

## Binding

A **Binding** maps canonical CEPIO semantics to a technology platform, data product or source system.

Examples:

- Fabric IQ binding;
- SAP adapter mapping;
- PI tag mapping;
- OSDU semantic projection;
- future spatial/3D bindings.
