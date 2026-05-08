import asyncio
import traceback

import db
import turn_manager


async def claim_job():
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            job = await conn.fetchrow(
                """
                SELECT id, campaign_id, job_type, payload
                FROM campaign_jobs
                WHERE status = 'pending'
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """
            )
            if not job:
                return None
            await conn.execute(
                "UPDATE campaign_jobs SET status = 'running', locked_at = now() WHERE id = $1",
                job["id"],
            )
            return dict(job)


async def complete_job(job_id):
    await db.execute(
        "UPDATE campaign_jobs SET status = 'completed', completed_at = now() WHERE id = $1",
        job_id,
    )


async def fail_job(job_id, error: str):
    await db.execute(
        "UPDATE campaign_jobs SET status = 'failed', error = $2, completed_at = now() WHERE id = $1",
        job_id,
        error[:2000],
    )


async def run_once():
    job = await claim_job()
    if not job:
        return False
    try:
        if job["job_type"] == "resolve_round":
            await turn_manager.process_resolve_round(str(job["campaign_id"]))
        else:
            # TODO: support summary generation and RAG background indexing jobs.
            pass
        await complete_job(job["id"])
    except Exception as exc:
        await fail_job(job["id"], "".join(traceback.format_exception_only(type(exc), exc)))
    return True


async def main():
    await db.connect()
    await db.install_schema()
    while True:
        did_work = await run_once()
        await asyncio.sleep(0.2 if did_work else 2.0)


if __name__ == "__main__":
    asyncio.run(main())
