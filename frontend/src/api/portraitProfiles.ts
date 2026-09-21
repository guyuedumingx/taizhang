import { api } from './index';
import { PortraitProfileFull } from '../types';

export async function getMyPortraitProfile(): Promise<PortraitProfileFull> {
  const response = await api.get(`/portrait/profiles/me`);
  return response.data;
}

export async function getPortraitProfileByEhr(ehrNo: string): Promise<PortraitProfileFull> {
  const response = await api.get(`/portrait/profiles/by-ehr/${ehrNo}`);
  return response.data;
}
