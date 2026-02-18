import { createClient } from '@vercel/kv';

// เชื่อมต่อ KV โดยอัตโนมัติผ่าน Environment Variables ของ Vercel
export const kv = createClient({
  url: process.env.KV_REST_API_URL!,
  token: process.env.KV_REST_API_TOKEN!,
});
