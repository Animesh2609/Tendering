import { DEMO } from './authApi';
import { http, readAllPages } from './http';
import { demoStaff } from '../../../api/demoStaff';
const id = encodeURIComponent;
export const auditorApi = {
  reports: async token => DEMO ? Promise.resolve(demoStaff.reports()) : readAllPages('/auditor/reports',token),
  flaggedTenders: async token => DEMO ? Promise.resolve(demoStaff.flagged()) : readAllPages('/auditor/tenders/flagged',token),
  completedTenders: async token => DEMO ? Promise.resolve(demoStaff.completed()) : readAllPages('/auditor/tenders/completed',token),
  async auditTender(tenderId,token) {
    if(DEMO)return demoStaff.audit(tenderId);
    return http(`/auditor/tenders/${id(tenderId)}/audit`,{method:'POST',token});
  },
  async proposal(bidId,token) {
    if(DEMO)throw new Error('The browser demo does not retain proposal files. Use live mode to download a submitted proposal.');
    return http(`/auditor/bids/${id(bidId)}/proposal`,{token,responseType:'blob'});
  },
  tender: async (tenderId,token) => DEMO ? Promise.resolve(demoStaff.tender(tenderId)) : http(`/tenders/${id(tenderId)}`,{token}),
  claim: async (reportId,token) => DEMO ? Promise.resolve(demoStaff.claim(reportId)) : http(`/auditor/reports/${id(reportId)}/claim`,{method:'POST',token}),
  resolve: async (reportId,issueConfirmed,resolutionNotes,token) => DEMO ? Promise.resolve(demoStaff.resolve(reportId,issueConfirmed,resolutionNotes)) : http(`/auditor/reports/${id(reportId)}/resolve`,{method:'POST',body:{issueConfirmed,resolutionNotes},token}),
  award: async (tenderId,winningBidId,remarks,token) => DEMO ? Promise.resolve(demoStaff.award(tenderId,winningBidId,remarks)) : http(`/auditor/tenders/${id(tenderId)}/award`,{method:'POST',body:{winningBidId,remarks},token}),
};
