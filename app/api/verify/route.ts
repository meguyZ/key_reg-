import { NextResponse } from 'next/server';
import { kv } from '@/lib/redis';

// API สำหรับ Python Client ยิงเข้ามาตรวจสอบ
export async function POST(req: Request) {
  try {
    const { key, hwid } = await req.json();

    if (!key || !hwid) {
      return NextResponse.json({ valid: false, message: "Missing data" }, { status: 400 });
    }

    // ดึงข้อมูล Key จาก Redis
    const keyData = await kv.hgetall(`license:${key}`);

    if (!keyData) {
      return NextResponse.json({ valid: false, message: "Key not found" });
    }

    // 1. ตรวจสอบสถานะ
    if (keyData.status === 'banned') {
        return NextResponse.json({ valid: false, message: "Key has been banned" });
    }
    
    // 2. ตรวจสอบ HWID Lock
    if (!keyData.hwid) {
        // ถ้ายังไม่มี HWID ผูกมัด (ใช้งานครั้งแรก) -> บันทึก HWID นี้
        await kv.hset(`license:${key}`, { ...keyData, hwid: hwid, activated_at: Date.now() });
        return NextResponse.json({ valid: true, message: "Activated successfully" });
    } else {
        // ถ้ามี HWID แล้ว -> ตรวจสอบว่าตรงกันไหม
        if (keyData.hwid === hwid) {
            return NextResponse.json({ valid: true, message: "Access granted" });
        } else {
            return NextResponse.json({ valid: false, message: "HWID Mismatch. Contact Admin." });
        }
    }

  } catch (error) {
    return NextResponse.json({ valid: false, message: "Server Error" }, { status: 500 });
  }
}
