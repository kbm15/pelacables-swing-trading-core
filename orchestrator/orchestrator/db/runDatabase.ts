// src/db/runDatabase.ts
import cassandra from 'cassandra-driver';
import { SCYLLA_KEYSPACE } from '../config';

export async function runDatabase(cluster: cassandra.Client) {
    const queries = [ /* table creation queries as in original code */ ];

    for (const query of queries) {
        try {
            await cluster.execute(query);
            console.log(`Table created with query: ${query}`);
        } catch (error) {
            console.error(`Failed to create table:`, error);
        }
    }
}
