import { Client as PostgresClient } from 'pg';
import mariadb from 'mariadb';
import { v4 as uuidv4 } from 'uuid';

// Database configuration
const postgresConfig = {
  user: 'postgres',
  host: 'localhost',
  database: 'testdb',
  password: 'password',
  port: 5432,
};

const mariaConfig = {
  user: 'mariauser',
  host: 'localhost',
  database: 'testdb',
  password: 'password',
  port: 3306,
};

// Queries for table creation
const queries = [
  `CREATE TABLE IF NOT EXISTS Users (
      user_id UUID PRIMARY KEY,
      telegram_id TEXT,
      username TEXT,
      email TEXT,
      date_created TIMESTAMP,
      status TEXT,
      preferences TEXT
  )`,
  `CREATE TABLE IF NOT EXISTS Subscriptions (
      subscription_id UUID PRIMARY KEY,
      user_id UUID,
      plan_type TEXT,
      start_date TIMESTAMP,
      end_date TIMESTAMP,
      status TEXT,
      auto_renewal BOOLEAN
  )`,
  `CREATE TABLE IF NOT EXISTS Indicator (
      indicator_id UUID PRIMARY KEY,
      name TEXT,
      description TEXT,
      strategy TEXT,
      configurations TEXT,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  )`,
  `CREATE TABLE IF NOT EXISTS TickerIndicator (
      ticker TEXT PRIMARY KEY,
      indicator_id UUID,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  )`,
  `CREATE TABLE IF NOT EXISTS Messages (
      message_id UUID PRIMARY KEY,
      indicator_id UUID,
      user_id UUID,
      message_content TEXT,
      message_type TEXT,
      sent_at TIMESTAMP
  )`,
  `CREATE TABLE IF NOT EXISTS Notifications (
      ticker TEXT,
      user_id UUID,
      subscribed_at TIMESTAMP,
      status TEXT,
      PRIMARY KEY (ticker, user_id)
  )`,
  `CREATE TABLE IF NOT EXISTS Operations (
      ticker TEXT,
      operation TEXT,
      indicator UUID,
      timestamp TIMESTAMP,
      PRIMARY KEY (ticker, timestamp)
  )`,
];

// Insert dummy data
const insertDummyData = [
  {
    table: 'Users',
    values: [
      `'${uuidv4()}'`,
      `'123456'`,
      `'test_user'`,
      `'test@example.com'`,
      `NOW()`,
      `'active'`,
      `'{"notifications": true}'`,
    ],
  },
  {
    table: 'Subscriptions',
    values: [
      `'${uuidv4()}'`,
      `'${uuidv4()}'`,
      `'premium'`,
      `NOW()`,
      `NOW() + INTERVAL '1 year'`,
      `'active'`,
      `TRUE`,
    ],
  },
  {
    table: 'Indicator',
    values: [
      `'${uuidv4()}'`,
      `'Test Indicator'`,
      `'Description of test indicator'`,
      `'strategy A'`,
      `'{}'`,
      `NOW()`,
      `NOW()`,
    ],
  },
];

// Helper function to benchmark inserts
async function benchmarkInserts(client: any, dbType: string) {
  console.log(`\nInserting dummy data into ${dbType} tables...`);
  for (const data of insertDummyData) {
    const query = `INSERT INTO ${data.table} VALUES (${data.values.join(', ')})`;
    const start = performance.now();
    await client.query(query);
    const end = performance.now();
    console.log(`${data.table} insert took ${end - start} ms`);
  }
}

// Benchmark read query
async function benchmarkRead(client: any, dbType: string, tableName: string) {
  console.log(`\nReading data from ${tableName} table in ${dbType}...`);
  const start = performance.now();
  await client.query(`SELECT * FROM ${tableName} LIMIT 10`);
  const end = performance.now();
  console.log(`${tableName} read took ${end - start} ms`);
}

// Benchmark dropping tables
async function benchmarkDrop(client: any, dbType: string) {
  console.log(`\nDropping tables in ${dbType}...`);
  const start = performance.now();
  for (const data of insertDummyData) {
    await client.query(`DROP TABLE IF EXISTS ${data.table}`);
  }
  const end = performance.now();
  console.log(`Dropping tables took ${end - start} ms`);
}

// Main function to run benchmarks
async function runBenchmarks() {
  // Postgres connection and setup
  const pgClient = new PostgresClient(postgresConfig);
  await pgClient.connect();
  console.log('\nConnected to PostgreSQL');

  for (const query of queries) {
    await pgClient.query(query);
  }

  await benchmarkInserts(pgClient, 'PostgreSQL');
  await benchmarkRead(pgClient, 'PostgreSQL', 'Users');
  await benchmarkDrop(pgClient, 'PostgreSQL');
  await pgClient.end();

  // MariaDB connection and setup
  const mariaClient = await mariadb.createConnection(mariaConfig);
  console.log('\nConnected to MariaDB');

  for (const query of queries) {
    await mariaClient.query(query);
  }

  await benchmarkInserts(mariaClient, 'MariaDB');
  await benchmarkRead(mariaClient, 'MariaDB', 'Users');
  await mariaClient.end();
}

runBenchmarks().catch((error) => console.error('Error:', error));
