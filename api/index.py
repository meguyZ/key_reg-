import { kv } from '@vercel/kv';
import { v4 as uuidv4 } from 'uuid';

// รหัสผ่าน Admin สำหรับหน้าจัดการ (เปลี่ยนตรงนี้)
const ADMIN_SECRET = "BRX-ADMIN-SECRET-2024";

export default async function handler(req, res) {
  // ตั้งค่า CORS ให้ Python และหน้า Admin เรียกใช้งานได้
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const { action } = req.body || req.query;

  try {
    // ==========================================
    // ส่วนของ CLIENT (Python เรียกใช้)
    // ==========================================
    
    // 1. ตรวจสอบคีย์ (Login)
    if (action === 'verify') {
      const { key, hwid } = req.body;
      if (!key || !hwid) return res.status(400).json({ status: 'error', message: 'Missing Data' });

      // ดึงข้อมูลคีย์จาก database
      const keyData = await kv.hget('license_keys', key);

      if (!keyData) {
        return res.status(401).json({ status: 'error', message: 'Invalid Key' });
      }

      if (keyData.status === 'suspended') {
        return res.status(403).json({ status: 'error', message: 'Key Suspended' });
      }

      // ถ้ายังไม่มี HWID ผูกไว้ (คีย์ใหม่) -> ผูกเลย
      if (!keyData.hwid) {
        keyData.hwid = hwid;
        keyData.activated_at = new Date().toISOString();
        await kv.hset('license_keys', { [key]: keyData });
        return res.status(200).json({ status: 'success', message: 'Activated', data: keyData });
      }

      // ถ้ามี HWID แล้ว -> เช็คว่าตรงกันไหม
      if (keyData.hwid !== hwid) {
        return res.status(403).json({ status: 'error', message: 'HWID Mismatch' });
      }

      // ผ่าน
      return res.status(200).json({ status: 'success', message: 'Verified', data: keyData });
    }

    // ==========================================
    // ส่วนของ ADMIN (Dashboard เรียกใช้)
    // ==========================================
    
    // ตรวจสอบรหัส Admin ก่อนทำคำสั่งด้านล่าง
    const { adminSecret } = req.body;
    if (adminSecret !== ADMIN_SECRET) {
        return res.status(401).json({ error: "Unauthorized" });
    }

    // 2. ดึงคีย์ทั้งหมด
    if (action === 'list_keys') {
      const keys = await kv.hgetall('license_keys') || {};
      return res.status(200).json(keys);
    }

    // 3. สร้างคีย์ใหม่
    if (action === 'create_key') {
      const { note, customKey } = req.body;
      const newKey = customKey || `BRX-${uuidv4().split('-')[0].toUpperCase()}-${uuidv4().split('-')[1].toUpperCase()}`;
      
      const keyObj = {
        key: newKey,
        hwid: null, // ยังไม่ผูก
        status: 'active',
        note: note || '',
        created_at: new Date().toISOString(),
        activated_at: null
      };

      await kv.hset('license_keys', { [newKey]: keyObj });
      return res.status(200).json({ status: 'success', key: keyObj });
    }

    // 4. ลบคีย์
    if (action === 'delete_key') {
      const { targetKey } = req.body;
      await kv.hdel('license_keys', targetKey);
      return res.status(200).json({ status: 'success' });
    }

    // 5. รีเซ็ต HWID (ย้ายเครื่อง)
    if (action === 'reset_hwid') {
      const { targetKey } = req.body;
      const keyData = await kv.hget('license_keys', targetKey);
      if (keyData) {
        keyData.hwid = null;
        await kv.hset('license_keys', { [targetKey]: keyData });
      }
      return res.status(200).json({ status: 'success' });
    }

    // 6. ระงับ/ปลดระงับ
    if (action === 'toggle_status') {
      const { targetKey } = req.body;
      const keyData = await kv.hget('license_keys', targetKey);
      if (keyData) {
        keyData.status = keyData.status === 'active' ? 'suspended' : 'active';
        await kv.hset('license_keys', { [targetKey]: keyData });
      }
      return res.status(200).json({ status: 'success' });
    }

    return res.status(404).json({ error: "Unknown Action" });

  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: "Internal Server Error" });
  }
}
