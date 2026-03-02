---
name: Redis Messaging Patterns
description: Use when the user asks about queues, message queues, job queues, reliable delivery, delayed tasks, scheduled jobs, event streaming, consumer groups, pub/sub, notifications, or message processing with Redis. Triggers on queries like "how to implement a queue", "reliable messaging", "Redis streams", "delayed execution".
version: 1.0.0
---

# Redis Messaging Patterns

Solutions for messaging, queuing, and event streaming use cases.

## Use Case → Pattern Mapping

| Use Case | Recommended Pattern |
|----------|---------------------|
| Simple FIFO queue | List-based Queue (LPUSH/RPOP) |
| Reliable message delivery | Reliable Queue (LMOVE) |
| Delayed/scheduled tasks | Delayed Queue (Sorted Set) |
| Multiple consumers, message persistence | Streams with Consumer Groups |
| Fire-and-forget notifications | Pub/Sub |

---

## Pattern 1: Simple FIFO Queue

**When to use:** Basic queue where occasional message loss is acceptable.

```python
# Producer
def enqueue(task):
    redis.lpush("queue:tasks", json.dumps(task))

# Consumer
def dequeue():
    task = redis.rpop("queue:tasks")
    return json.loads(task) if task else None
```

**Key commands:** `LPUSH`, `RPOP`, `LLEN`

**Pros:** Simple, fast
**Cons:** Message lost if consumer crashes after RPOP

---

## Pattern 2: Reliable Queue

**When to use:** When at-least-once delivery guarantee is required.

**How it works:** Use LMOVE to atomically transfer messages to a processing list, enabling recovery if consumers crash.

```python
# Consumer with reliability
def process_task():
    # Atomically move from pending to processing
    task = redis.lmove("queue:tasks", "queue:processing", "RIGHT", "LEFT")

    if task:
        try:
            data = json.loads(task)
            # Process the task
            do_work(data)
            # Remove from processing queue on success
            redis.lrem("queue:processing", 1, task)
        except Exception as e:
            # Task remains in processing queue for recovery
            log_error(e)

# Recovery: re-queue stuck tasks
def recover_stuck_tasks(timeout=300):
    now = time.time()
    tasks = redis.lrange("queue:processing", 0, -1)
    for task in tasks:
        data = json.loads(task)
        if now - data["started_at"] > timeout:
            redis.lmove("queue:processing", "queue:tasks", "RIGHT", "LEFT")
```

**Key commands:** `LMOVE`, `LREM`, `LRANGE`

**Pros:** At-least-once delivery, crash recovery
**Cons:** Slightly more complex, idempotent processing needed

---

## Pattern 3: Delayed Queue

**When to use:** Schedule tasks for future execution.

**How it works:** Use a Sorted Set where the score is the Unix timestamp when the task should run.

```python
# Schedule a task
def schedule_task(task, delay_seconds):
    execute_at = time.time() + delay_seconds
    redis.zadd("queue:delayed", {json.dumps(task): execute_at})

# Worker to process delayed tasks
def process_delayed():
    now = time.time()

    # Get tasks ready to execute
    ready = redis.zrangebyscore("queue:delayed", 0, now)

    for task_json in ready:
        # Remove from delayed queue
        if redis.zrem("queue:delayed", task_json):
            task = json.loads(task_json)
            # Move to active queue or process directly
            redis.lpush("queue:tasks", task_json)

# Run worker periodically
while True:
    process_delayed()
    time.sleep(1)
```

**Key commands:** `ZADD`, `ZRANGEBYSCORE`, `ZREM`

**Pros:** Precise scheduling, efficient time-based queries
**Cons:** Polling required (or use keyspace notifications)

---

## Pattern 4: Redis Streams with Consumer Groups

**When to use:** Multiple consumers, message persistence, acknowledgment, and historical replay.

**How it works:** Streams provide a persistent, append-only log with consumer group support.

```python
# Producer
def publish_event(stream, event):
    return redis.xadd(stream, event)

# Consumer with consumer group
def consume_events(stream, group, consumer):
    # Create consumer group if not exists
    try:
        redis.xgroup_create(stream, group, id="0")
    except:
        pass  # Group already exists

    while True:
        # Read new messages
        messages = redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=10,
            block=5000
        )

        for stream_name, entries in messages:
            for message_id, data in entries:
                try:
                    process_event(data)
                    # Acknowledge successful processing
                    redis.xack(stream, group, message_id)
                except Exception as e:
                    log_error(e)
                    # Message will be redelivered

# Claim pending messages (for crashed consumers)
def claim_abandoned(stream, group, consumer, min_idle_time=60000):
    pending = redis.xpending_range(stream, group, "-", "+", 10, min_idle_time)
    for p in pending:
        # Claim the message
        claimed = redis.xclaim(stream, group, consumer, min_idle_time, [p["message_id"]])
        # Reprocess...
```

**Key commands:** `XADD`, `XREADGROUP`, `XACK`, `XGROUP CREATE`, `XPENDING`, `XCLAIM`

**Pros:** Persistent, replayable, multiple consumers, exactly-once semantics possible
**Cons:** More complex, memory management needed (XTRIM)

### Stream Memory Management

```python
# Limit stream length
redis.xadd("mystream", {"data": "..."}, maxlen=10000)

# Or trim periodically
redis.xtrim("mystream", maxlen=10000)
```

---

## Pattern 5: Pub/Sub

**When to use:** Fire-and-forget notifications, chat, live updates where missed messages are acceptable.

```python
# Publisher
def notify(channel, message):
    redis.publish(channel, json.dumps(message))

# Subscriber
def subscribe(channel):
    pubsub = redis.pubsub()
    pubsub.subscribe(channel)

    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            handle_notification(data)
```

**Key commands:** `PUBLISH`, `SUBSCRIBE`, `PSUBSCRIBE` (pattern subscribe)

**Pros:** Simple, real-time
**Cons:** No persistence, no acknowledgment, messages lost if no subscribers

---

## Comparison Table

| Feature | List Queue | Reliable Queue | Delayed Queue | Streams | Pub/Sub |
|---------|------------|----------------|---------------|---------|---------|
| Persistence | ✅ | ✅ | ✅ | ✅ | ❌ |
| Acknowledgment | ❌ | ✅ | ✅ | ✅ | ❌ |
| Multiple Consumers | ❌ | ❌ | ❌ | ✅ | ✅ |
| Historical Replay | ❌ | ❌ | ❌ | ✅ | ❌ |
| Delayed Delivery | ❌ | ❌ | ✅ | ❌ | ❌ |

---

## Anti-Patterns to Avoid

1. **Using RPOPLPUSH in Redis 6.2+** → Use LMOVE instead (deprecated)
2. **Unbounded Streams** → Use MAXLEN or XTRIM
3. **Pub/Sub for critical messages** → Use Streams instead
4. **No error handling in consumers** → Messages stuck in pending

## Quick Reference

```
# Simple Queue
LPUSH queue:tasks task_data
RPOP queue:tasks

# Reliable Queue
LMOVE queue:tasks queue:processing RIGHT LEFT
LREM queue:processing 1 task_data

# Delayed Queue
ZADD queue:delayed <timestamp> task_data
ZRANGEBYSCORE queue:delayed 0 <now>

# Streams
XADD stream * field value
XREADGROUP GROUP group consumer STREAMS stream >
XACK stream group message_id

# Pub/Sub
PUBLISH channel message
SUBSCRIBE channel
```
