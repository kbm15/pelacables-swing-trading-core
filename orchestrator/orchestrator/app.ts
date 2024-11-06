// src/app.ts
import { orchestrate } from './orchestrator';

orchestrate().catch(console.error);
