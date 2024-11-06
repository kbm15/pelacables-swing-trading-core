// src/db/indicatorQueries.ts
import cassandra from 'cassandra-driver';
import { SCYLLA_KEYSPACE, INDICATORS_STRATEGIES } from '../config';

export async function insertIndicators(client: cassandra.Client) {
    // Same logic to insert indicators as in original code
}

export async function countIndicators(cluster: cassandra.Client): Promise<number> {
    const query = `SELECT COUNT(*) FROM ${SCYLLA_KEYSPACE}.Indicator`;
    const result = await cluster.execute(query, [], { prepare: true });
    return result.rows[0]['count'];
}
