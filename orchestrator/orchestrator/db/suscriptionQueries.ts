import { Client as PostgresClient } from 'pg';
import type { Subscription } from '../types';

// 1. Get all subscriptions grouped by ticker
export async function getSubscriptions(client: PostgresClient): Promise<Subscription[]> {
  const query = `
    SELECT ticker, ARRAY_AGG(telegram_id) AS userIds
    FROM Notifications
    GROUP BY ticker
  `;
  const result = await client.query(query);
  return result.rows.map(row => ({
    ticker: row.ticker,
    userIds: row.userids, // Ensure correct lowercase if needed by pg
  }));
}

// 2. Get subscriptions for a specific user
export async function getUserSubscriptions(userId: string, client: PostgresClient): Promise<string[]> {
  const query = `
    SELECT ticker
    FROM Notifications
    WHERE telegram_id = $1
  `;
  const result = await client.query(query, [userId]);
  return result.rows.map(row => row.ticker);
}

async function addUser(user: string, client: PostgresClient)  {
  const query = `
    INSERT INTO Users (telegram_id)
    VALUES ($1)
    ON CONFLICT DO NOTHING
  `;
  await client.query(query, [user]);
}

// 3. Add a user subscription to a ticker (do nothing if already exists)
export async function addUserSubscription(ticker: string, userId: string, status: string = 'active', client: PostgresClient) {
  await addUser(userId, client);
  const query = `
    INSERT INTO Notifications (ticker, telegram_id, subscribed_at, status)
    VALUES ($1, $2, NOW(), $3)
    ON CONFLICT DO NOTHING
  `;
  await client.query(query, [ticker, userId, status]);
}

// 4. Remove a user subscription for a specific ticker
export async function removeUserSubscription(ticker: string, userId: string, client: PostgresClient) {
  const query = `
    DELETE FROM Notifications
    WHERE ticker = $1 AND telegram_id = $2
  `;
  await client.query(query, [ticker, userId]);
}