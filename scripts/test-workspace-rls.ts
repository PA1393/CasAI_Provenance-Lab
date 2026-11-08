// Real PostgreSQL RLS rehearsal, entirely in memory. No hosted account/data touched.
import { PGlite } from "@electric-sql/pglite";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const db = new PGlite();
const a = "11111111-1111-4111-8111-111111111111";
const b = "22222222-2222-4222-8222-222222222222";
try {
  await db.exec(`
    CREATE ROLE authenticated NOLOGIN;
    CREATE ROLE anon NOLOGIN;
    CREATE ROLE service_role NOLOGIN BYPASSRLS;
    CREATE SCHEMA auth;
    CREATE TABLE auth.users(id uuid PRIMARY KEY);
    CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS
      $$ SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
    GRANT USAGE ON SCHEMA auth TO authenticated;
    GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated;
    INSERT INTO auth.users VALUES ('${a}'), ('${b}');
  `);
  // Start with the actual initial schema. Additional columns do not change these policies.
  await db.exec(await readFile(new URL("../apps/api/migrations/001_init.sql", import.meta.url), "utf8"));
  for (const migration of ["002_phase1_schema.sql", "006_research_object_sequence.sql", "007_confirmed_input_link.sql"]) {
    await db.exec(await readFile(new URL(`../apps/api/migrations/${migration}`, import.meta.url), "utf8"));
  }
  const legacy = (await db.query<{ research_object_id: string }>(`
    INSERT INTO public.research_objects(name,input_filename,input_file_type,pdb_id,ro_hash,status)
    VALUES ('legacy-demo','demo.fasta','fasta','','sha256:legacy','ready') RETURNING research_object_id
  `)).rows[0].research_object_id;
  await db.exec(await readFile(new URL("../apps/api/migrations/008_personal_workspaces.sql", import.meta.url), "utf8"));
  async function asUser(id: string) {
    await db.exec("RESET ROLE");
    await db.query("SELECT set_config('request.jwt.claim.sub', $1, false)", [id]);
    await db.exec("SET ROLE authenticated");
  }
  await asUser(a);
  assert.equal((await db.query("SELECT * FROM research_objects")).rows.length, 0, "legacy data hidden");
  const folder = (await db.query<{ folder_id: string }>("INSERT INTO research_folders(name) VALUES ('Project A') RETURNING folder_id")).rows[0].folder_id;
  const input = (await db.query<{ research_object_id: string }>(`
    INSERT INTO research_objects(name,input_filename,input_file_type,pdb_id,ro_hash,status,folder_id)
    VALUES ('rice','rice.fasta','fasta','','sha256:example','ready',$1) RETURNING research_object_id
  `, [folder])).rows[0].research_object_id;
  const run = (await db.query<{ run_id: string }>("INSERT INTO runs(research_object_id,prompt,status) VALUES ($1,'CBE demo','completed') RETURNING run_id", [input])).rows[0].run_id;
  await db.query("INSERT INTO provenance_events(run_id,event_type,message,stage) VALUES ($1,'test','example','input')", [run]);
  await db.query(`INSERT INTO results(run_id,research_object_id,edited_sequence,edit_summary,off_target_score,on_target_score)
    VALUES ($1,$2,'ACGT','example',0,0)`, [run, input]);
  await db.query("UPDATE runs SET folder_id=$1 WHERE run_id=$2", [folder, run]);
  assert.equal((await db.query("SELECT * FROM results")).rows.length, 1);
  await asUser(b);
  await assert.rejects(db.query("TRUNCATE research_objects CASCADE"));
  for (const table of ["research_folders", "research_objects", "runs", "results", "provenance_events"]) {
    assert.equal((await db.query(`SELECT * FROM ${table}`)).rows.length, 0, `B cannot list A's ${table}`);
  }
  assert.equal((await db.query("UPDATE runs SET folder_id=NULL WHERE run_id=$1 RETURNING run_id", [run])).rows.length, 0);
  await assert.rejects(db.query("INSERT INTO runs(research_object_id,prompt,status) VALUES ($1,'attack','queued')", [input]));
  await assert.rejects(db.query("INSERT INTO provenance_events(run_id,event_type,message,stage) VALUES ($1,'attack','x','input')", [run]));
  await assert.rejects(db.query("INSERT INTO research_folders(owner_id,name) VALUES ($1,'spoof')", [a]));
  await assert.rejects(db.query(`INSERT INTO research_objects(name,input_filename,input_file_type,pdb_id,ro_hash,status,folder_id)
    VALUES ('attack','x','fasta','','x','ready',$1)`, [folder]));
  await assert.rejects(db.query(`INSERT INTO results(run_id,research_object_id,edited_sequence,edit_summary,off_target_score,on_target_score)
    VALUES ($1,$2,'ACGT','attack',0,0)`, [run, input]));
  await asUser(a);
  await assert.rejects(db.query("UPDATE research_objects SET owner_id=$1 WHERE research_object_id=$2", [b, input]));
  await db.exec("RESET ROLE");
  assert.equal((await db.query("SELECT * FROM research_objects WHERE research_object_id=$1", [legacy])).rows.length, 1, "legacy row preserved");
  await db.exec("SET ROLE anon");
  await assert.rejects(db.query("SELECT * FROM research_objects"));
  await db.exec("RESET ROLE");
  await db.exec(await readFile(new URL("../apps/api/migrations/009_isolated_demo_and_run_issues.sql", import.meta.url), "utf8"));
  await db.exec("SET ROLE service_role");
  for (const table of ["demo_research_objects", "demo_runs", "demo_results", "demo_provenance_events", "demo_research_folders"]) {
    assert.equal((await db.query(`SELECT * FROM ${table}`)).rows.length, 0, "No account/legacy rows copied into demo");
  }
  const demoFolder = (await db.query<{ folder_id: string }>("INSERT INTO demo_research_folders(name) VALUES ('Demo project') RETURNING folder_id")).rows[0].folder_id;
  const demoInput = (await db.query<{ research_object_id: string }>(`
    INSERT INTO demo_research_objects(name,input_filename,input_file_type,pdb_id,ro_hash,status,folder_id)
    VALUES ('Demo','synthetic.fasta','fasta','','sha256:demo','ready',$1) RETURNING research_object_id
  `, [demoFolder])).rows[0].research_object_id;
  const demoRun = (await db.query<{ run_id: string }>(`
    INSERT INTO demo_runs(research_object_id,prompt,status,folder_id,failure)
    VALUES ($1,'No site','failed',$2,'{"stage":"extract","code":"no_compatible_site"}') RETURNING run_id
  `, [demoInput, demoFolder])).rows[0].run_id;
  assert.equal((await db.query<{ failure: { code: string } }>("SELECT failure FROM demo_runs WHERE run_id=$1", [demoRun])).rows[0].failure.code, "no_compatible_site");
  await assert.rejects(db.query("INSERT INTO demo_runs(research_object_id,prompt,status) VALUES ($1,'Cross namespace','running')", [input]));
  await db.exec("RESET ROLE; SET ROLE anon");
  await assert.rejects(db.query("SELECT * FROM demo_runs"));
  await db.exec("RESET ROLE; SET ROLE authenticated");
  await assert.rejects(db.query("SELECT * FROM demo_research_objects"));
  console.log("PASS: PostgreSQL migration, per-user defaults, legacy isolation, child reads/writes, folder moves, spoofing and anonymous denial");
  console.log("PASS: isolated demo namespace, no data copying, demo folders/failure records and cross-namespace/anonymous denial");
} finally { await db.close(); }

// Demo-only deployments must not depend on the deferred account migration.
const demoOnly = new PGlite();
try {
  await demoOnly.exec("CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS;");
  for (const migration of ["001_init.sql", "002_phase1_schema.sql", "006_research_object_sequence.sql", "007_confirmed_input_link.sql", "009_isolated_demo_and_run_issues.sql"]) {
    await demoOnly.exec(await readFile(new URL(`../apps/api/migrations/${migration}`, import.meta.url), "utf8"));
  }
  await demoOnly.exec("SET ROLE service_role");
  const created = await demoOnly.query("INSERT INTO demo_research_folders(name) VALUES ('No login or account migration') RETURNING folder_id");
  assert.equal(created.rows.length, 1);
  assert.equal((await demoOnly.query("SELECT * FROM demo_research_objects")).rows.length, 0);
  console.log("PASS: demo migration also works with account migration 008 absent.");
} finally { await demoOnly.close(); }
