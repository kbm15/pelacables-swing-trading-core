// src/db/initDatabase.ts
import cassandra from 'cassandra-driver';
import { SCYLLA_HOST, SCYLLA_DATACENTER, SCYLLA_USERNAME, SCYLLA_PASSWORD } from '../config';

export async function initDatabase() {
    const cluster = new cassandra.Client({
        contactPoints: [SCYLLA_HOST],
        localDataCenter: SCYLLA_DATACENTER,
        credentials: { username: SCYLLA_USERNAME, password: SCYLLA_PASSWORD },
    });

    await cluster.execute(`
        CREATE KEYSPACE IF NOT EXISTS ${SCYLLA_KEYSPACE}
        WITH REPLICATION = { 'class': 'SimpleStrategy', 'replication_factor': 1 }
        AND durable_writes = true;
    `);
    console.log("Initialized Cassandra database.");
    return cluster;
}
