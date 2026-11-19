package icu.telepathystudios.puretender.service.audit;

import icu.telepathystudios.puretender.dto.audit.IntegrityReportResponse;
import icu.telepathystudios.puretender.dto.audit.ResolveIntegrityReportRequest;
import icu.telepathystudios.puretender.dto.audit.AwardHeldTenderRequest;
import icu.telepathystudios.puretender.dto.audit.AuditorBidAuditResponse;
import icu.telepathystudios.puretender.dto.audit.AuditorTenderAuditResponse;
import icu.telepathystudios.puretender.dto.audit.AuditorTenderSummaryResponse;
import icu.telepathystudios.puretender.dto.bid.BidProposalDownload;
import icu.telepathystudios.puretender.dto.tender.TenderAwardResponse;
import icu.telepathystudios.puretender.model.classes.Bid;
import icu.telepathystudios.puretender.model.classes.BidEvaluation;
import icu.telepathystudios.puretender.model.classes.BidDocument;
import icu.telepathystudios.puretender.model.classes.IntegrityReport;
import icu.telepathystudios.puretender.model.classes.Tender;
import icu.telepathystudios.puretender.model.classes.TenderAward;
import icu.telepathystudios.puretender.model.classes.User;
import icu.telepathystudios.puretender.model.enums.*;
import icu.telepathystudios.puretender.repo.bid.BidEvaluationRepo;
import icu.telepathystudios.puretender.repo.bid.BidDocumentRepo;
import icu.telepathystudios.puretender.repo.bid.BidRepo;
import icu.telepathystudios.puretender.repo.AuthRepo;
import icu.telepathystudios.puretender.repo.IntegrityReportRepo;
import icu.telepathystudios.puretender.repo.tender.TenderAwardRepo;
import icu.telepathystudios.puretender.repo.tender.TenderRepo;
import icu.telepathystudios.puretender.service.blockchain.BlockchainRecordService;
import icu.telepathystudios.puretender.service.blockchain.DocumentHashService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AuditorService {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final List<BidStatus> AUDITABLE_BID_STATUSES = List.of(
            BidStatus.OPENED, BidStatus.UNDER_EVALUATION,
            BidStatus.EVALUATED, BidStatus.SELECTED, BidStatus.NOT_SELECTED
    );

    private final AuthRepo authRepo;
    private final IntegrityReportRepo integrityReportRepo;
    private final TenderAwardRepo tenderAwardRepo;
    private final TenderRepo tenderRepo;
    private final BidRepo bidRepo;
    private final BidEvaluationRepo bidEvaluationRepo;
    private final BidDocumentRepo bidDocumentRepo;
    private final DocumentHashService documentHashService;
    private final BlockchainRecordService blockchainRecordService;
    private final IntegrityReportService integrityReportService;

    //region Auditor tender queues and integrity audits
    @Transactional(readOnly = true)
    public Page<AuditorTenderSummaryResponse> getReviewQueue(
            Authentication authentication,
            Pageable pageable
    ) {
        getVerifiedAuditor(authentication);
        return tenderRepo.findAllByStatus(TenderStatus.UNDER_EVALUATION, pageable)
                .map(tender -> new AuditorTenderSummaryResponse(
                        tender.getId(), tender.getTitle(), tender.getAuthority().getFullName(),
                        tender.getStatus(), null, null, 0, null
                ));
    }

    @Transactional(readOnly = true)
    public Page<AuditorTenderSummaryResponse> getFlaggedTenders(
            Authentication authentication,
            Pageable pageable
    ) {
        getVerifiedAuditor(authentication);
        return tenderRepo.findAllByStatus(TenderStatus.ON_HOLD, pageable)
                .map(tender -> new AuditorTenderSummaryResponse(
                        tender.getId(), tender.getTitle(), tender.getAuthority().getFullName(),
                        tender.getStatus(),
                        integrityReportRepo.findFirstByTender_IdOrderByCreatedAtDesc(tender.getId())
                                .map(IntegrityReport::getCreatedAt).orElse(null),
                        null,
                        integrityReportRepo.countByTender_Id(tender.getId()),
                        null
                ));
    }

    @Transactional(readOnly = true)
    public Page<AuditorTenderSummaryResponse> getCompletedTenders(
            Authentication authentication,
            Pageable pageable
    ) {
        getVerifiedAuditor(authentication);
        return tenderAwardRepo.findAll(pageable).map(award -> {
            Tender tender = award.getTender();
            return new AuditorTenderSummaryResponse(
                    tender.getId(), tender.getTitle(), tender.getAuthority().getFullName(),
                    tender.getStatus(), null, award.getAwardedAt(),
                    integrityReportRepo.countByTender_Id(tender.getId()),
                    award.getWinningBid().getId()
            );
        });
    }

    @Transactional
    public AuditorTenderAuditResponse auditTender(
            UUID tenderId,
            Authentication authentication
    ) {
        getVerifiedAuditor(authentication);
        Tender tender = tenderRepo.findById(tenderId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Tender not found."
                ));
        if (tender.getStatus() != TenderStatus.UNDER_EVALUATION
                && tender.getStatus() != TenderStatus.ON_HOLD
                && tender.getStatus() != TenderStatus.AWARDED) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Auditors can audit tenders under evaluation, on hold, or awarded."
            );
        }

        List<String> verificationMessages = new ArrayList<>();
        String tenderRecordId = "TENDER:" + tender.getId();
        LedgerCheck tenderCheck = checkLedgerRecord(
                tenderRecordId,
                blockchainRecordService.hashTender(tender)
        );
        if (tenderCheck.message() != null) verificationMessages.add(tenderCheck.message());

        boolean canCreateReports = tender.getStatus() == TenderStatus.UNDER_EVALUATION
                || (tender.getStatus() == TenderStatus.ON_HOLD
                && !tenderAwardRepo.existsByTender_Id(tenderId));
        if (canCreateReports && tenderCheck.status() == IntegrityStatus.DISCREPANCY_FOUND) {
            integrityReportService.createSystemReport(
                    tenderId, null,
                    tenderCheck.missingRecord()
                            ? IntegrityReportType.MISSING_BLOCKCHAIN_RECORD
                            : IntegrityReportType.UNEXPECTED_TENDER_MODIFICATION,
                    tenderCheck.message(),
                    tenderRecordId
            );
        }

        List<Bid> bids = bidRepo.findAllByTender_IdAndStatusIn(
                tenderId, AUDITABLE_BID_STATUSES
        );
        List<AuditorBidAuditResponse> bidResponses = new ArrayList<>();
        IntegrityStatus databaseStatus = IntegrityStatus.NOT_CHECKED;
        for (Bid bid : bids) {
            BidDocument document = bidDocumentRepo.findByBid_Id(bid.getId()).orElse(null);
            IntegrityStatus dbStatus;
            IntegrityStatus chainStatus = IntegrityStatus.NOT_CHECKED;
            String payloadHash = null;

            if (document == null || !documentHashService.matches(
                    document.getFileData(), document.getSha256Hash())) {
                dbStatus = IntegrityStatus.DISCREPANCY_FOUND;
                String message = document == null
                        ? "Proposal PDF is missing for bid " + bid.getId() + "."
                        : "Stored proposal PDF hash does not match bid " + bid.getId() + ".";
                verificationMessages.add(message);
                if (canCreateReports) {
                    integrityReportService.createSystemReport(
                            tenderId, bid.getId(), IntegrityReportType.INVALID_DOCUMENT_HASH,
                            message, "BID:" + bid.getId()
                    );
                }
            } else {
                dbStatus = IntegrityStatus.VERIFIED;
                payloadHash = blockchainRecordService.hashBid(bid, document);
                LedgerCheck bidCheck = checkLedgerRecord("BID:" + bid.getId(), payloadHash);
                chainStatus = bidCheck.status();
                if (bidCheck.message() != null) verificationMessages.add(bidCheck.message());
                if (canCreateReports && chainStatus == IntegrityStatus.DISCREPANCY_FOUND) {
                    integrityReportService.createSystemReport(
                            tenderId, bid.getId(),
                            bidCheck.missingRecord()
                                    ? IntegrityReportType.MISSING_BLOCKCHAIN_RECORD
                                    : IntegrityReportType.HASH_MISMATCH,
                            bidCheck.message(), "BID:" + bid.getId()
                    );
                }
            }

            bidResponses.add(new AuditorBidAuditResponse(
                    bid.getId(), bid.getContractor().getId(), bid.getContractor().getFullName(),
                    bid.getQuotedAmount(), bid.getStatus(), bid.getOpenedAt(), document != null,
                    dbStatus, chainStatus,
                    document == null ? null : document.getSha256Hash()
            ));
        }

        if (!bidResponses.isEmpty()) {
            databaseStatus = bidResponses.stream().anyMatch(bid ->
                    bid.databaseIntegrity() == IntegrityStatus.DISCREPANCY_FOUND)
                    ? IntegrityStatus.DISCREPANCY_FOUND
                    : bidResponses.stream().allMatch(bid ->
                            bid.databaseIntegrity() == IntegrityStatus.VERIFIED)
                            ? IntegrityStatus.VERIFIED
                            : IntegrityStatus.NOT_CHECKED;
        }

        List<IntegrityReportResponse> reports = integrityReportRepo
                .findAllByTender_IdOrderByCreatedAtDesc(tenderId)
                .stream().map(this::mapToIntegrityReportResponse).toList();
        boolean unavailable = verificationMessages.stream()
                .anyMatch(message -> message.startsWith("Could not verify blockchain record"));
        return new AuditorTenderAuditResponse(
                tender.getId(), tender.getTitle(), tender.getAuthority().getFullName(),
                tender.getDescription(), tender.getStatus(), databaseStatus,
                tenderCheck.status(), bidResponses, reports,
                verificationMessages.isEmpty() ? null : String.join(" ", verificationMessages),
                unavailable
        );
    }

    @Transactional(readOnly = true)
    public BidProposalDownload downloadProposal(
            UUID bidId,
            Authentication authentication
    ) {
        getVerifiedAuditor(authentication);
        Bid bid = bidRepo.findById(bidId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Bid not found."
                ));
        if (bid.getTender().getStatus() != TenderStatus.ON_HOLD
                && bid.getTender().getStatus() != TenderStatus.AWARDED) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Auditors can download proposals for held or completed tenders."
            );
        }
        BidDocument document = bidDocumentRepo.findByBid_Id(bidId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Proposal PDF not found."
                ));
        if (!documentHashService.matches(document.getFileData(), document.getSha256Hash())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT, "Stored proposal PDF failed its integrity check."
            );
        }
        return new BidProposalDownload(
                document.getFileData(), document.getFileName(), document.getContentType()
        );
    }

    //endregion

    //region Integrity report lifecycle and tender awards
    // 1. List all integrity reports
    @Transactional(readOnly = true)
    public Page<IntegrityReportResponse> getReports(
            Authentication authentication,
            Pageable pageable
    ) {
        getVerifiedAuditor(authentication);

        return integrityReportRepo
                .findAllByOrderByCreatedAtDesc(pageable)
                .map(this::mapToIntegrityReportResponse);
    }

    // 2. View a particular report
    @Transactional(readOnly = true)
    public IntegrityReportResponse getReport(
            UUID reportId,
            Authentication authentication
    ) {
        getVerifiedAuditor(authentication);

        IntegrityReport report = getIntegrityReport(reportId);

        return mapToIntegrityReportResponse(report);
    }

    // 3. Claim a report for investigation
    @Transactional
    public IntegrityReportResponse claimReport(
            UUID reportId,
            Authentication authentication
    ) {
        User auditor = getVerifiedAuditor(authentication);

        IntegrityReport report = getIntegrityReport(reportId);

        if (report.getStatus() != IntegrityReportStatus.OPEN) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "Only open reports can be claimed."
            );
        }

        if (report.getAssignedAuditor() != null) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "This report has already been assigned."
            );
        }

        report.setAssignedAuditor(auditor);
        report.setStatus(IntegrityReportStatus.UNDER_REVIEW);

        IntegrityReport saved = integrityReportRepo.save(report);

        return mapToIntegrityReportResponse(saved);
    }

    // 4. Resolve a report
    @Transactional
    public IntegrityReportResponse resolveReport(
            UUID reportId,
            ResolveIntegrityReportRequest request,
            Authentication authentication
    ) {
        User auditor = getVerifiedAuditor(authentication);

        IntegrityReport report = getIntegrityReport(reportId);

        if (report.getStatus() != IntegrityReportStatus.UNDER_REVIEW) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "This report is not currently under review."
            );
        }

        if (report.getAssignedAuditor() == null ||
                !report.getAssignedAuditor().getId().equals(auditor.getId())) {

            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Only the assigned auditor can resolve this report."
            );
        }

        report.setResolutionNotes(request.resolutionNotes());
        report.setResolvedAt(Instant.now());

        UUID tenderId = report.getTender().getId();

        if (request.issueConfirmed()) {

            report.setStatus(IntegrityReportStatus.RESOLVED);

            Tender tender = report.getTender();
            if (tender.getStatus() != TenderStatus.ON_HOLD
                    || tenderAwardRepo.existsByTender_Id(tenderId)) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "Only a flagged, unawarded tender can be voided by this workflow."
                );
            }

            tender.setStatus(TenderStatus.VOIDED);

        } else {

            report.setStatus(IntegrityReportStatus.DISMISSED);

            if (report.getTender().getStatus() != TenderStatus.ON_HOLD) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "The tender is no longer on hold."
                );
            }
        }

        IntegrityReport saved = integrityReportRepo.save(report);

        return mapToIntegrityReportResponse(saved);
    }

    @Transactional
    public TenderAwardResponse awardHeldTender(
            UUID tenderId,
            AwardHeldTenderRequest request,
            Authentication authentication
    ) {
        User auditor = getVerifiedAuditor(authentication);
        Tender tender = tenderRepo.findById(tenderId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Tender not found."
                ));

        if (tender.getStatus() != TenderStatus.ON_HOLD
                || tenderAwardRepo.existsByTender_Id(tenderId)) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "Only a held, unawarded tender can be awarded through this workflow."
            );
        }

        if (integrityReportRepo.existsByTender_IdAndStatusIn(
                tenderId,
                List.of(IntegrityReportStatus.OPEN, IntegrityReportStatus.UNDER_REVIEW))) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "All integrity reports must be resolved before the tender can be awarded."
            );
        }

        Bid winningBid = bidRepo.findById(request.winningBidId())
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Winning bid not found."
                ));
        if (!winningBid.getTender().getId().equals(tenderId)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "The selected bid does not belong to this tender."
            );
        }

        BidEvaluation winningEvaluation = bidEvaluationRepo.findByBid_Id(winningBid.getId())
                .filter(evaluation -> evaluation.getStatus() == EvaluationStatus.FINALIZED)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "The selected bid must have a finalized evaluation."
                ));
        if (winningBid.getStatus() != BidStatus.EVALUATED) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "The selected bid is not ready to be awarded."
            );
        }

        List<Bid> awardableBids = bidRepo.findAllByTender_IdAndStatusIn(
                tenderId,
                List.of(BidStatus.SUBMITTED, BidStatus.OPENED,
                        BidStatus.UNDER_EVALUATION, BidStatus.EVALUATED)
        );
        if (awardableBids.stream().anyMatch(bid -> bid.getStatus() != BidStatus.EVALUATED)) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "Every submitted bid must be evaluated before the tender can be awarded."
            );
        }

        List<Bid> evaluatedBids = awardableBids;
        for (Bid bid : evaluatedBids) {
            bid.setStatus(bid.getId().equals(winningBid.getId())
                    ? BidStatus.SELECTED : BidStatus.NOT_SELECTED);
        }
        bidRepo.saveAll(evaluatedBids);

        TenderAward award = new TenderAward();
        award.setTender(tender);
        award.setWinningBid(winningBid);
        award.setTriggeredBy(auditor);
        award.setRemarks(request.remarks());
        TenderAward savedAward = tenderAwardRepo.save(award);
        tender.setStatus(TenderStatus.AWARDED);
        tenderRepo.save(tender);

        return new TenderAwardResponse(
                savedAward.getId(), tender.getId(), tender.getTitle(),
                winningBid.getId(), winningBid.getContractor().getFullName(),
                winningBid.getQuotedAmount(), winningEvaluation.getTechnicalScore(),
                winningEvaluation.getFinancialScore(), winningEvaluation.getTotalScore(),
                auditor.getId(), auditor.getFullName(), savedAward.getRemarks(),
                savedAward.getVerificationStatus(), savedAward.getAwardedAt()
        );
    }


    //endregion

    //region Auditor authorization, ledger checks, and response mapping

    private User getVerifiedAuditor(Authentication authentication) {

        if (authentication == null || authentication.getName() == null) {
            throw new ResponseStatusException(
                    HttpStatus.UNAUTHORIZED,
                    "Authentication is required."
            );
        }

        User auditor = authRepo.findByEmail(authentication.getName())
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.UNAUTHORIZED,
                        "Auditor account not found."
                ));

        if (auditor.getRole() != Role.AUDITOR) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Only auditors can access this resource."
            );
        }

        if (auditor.getStatus() != AccountStatus.VERIFIED) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "Your account is not verified."
            );
        }

        return auditor;
    }

    private LedgerCheck checkLedgerRecord(String recordId, String expectedHash) {
        try {
            if (!blockchainRecordService.integrityRecordExists(recordId)) {
                return new LedgerCheck(
                        IntegrityStatus.DISCREPANCY_FOUND,
                        "Blockchain record " + recordId + " is missing.",
                        true
                );
            }

            JsonNode record = OBJECT_MAPPER.readTree(
                    blockchainRecordService.readIntegrityRecord(recordId)
            );
            String actualHash = record.path("payloadHash").asText(null);
            if (actualHash == null || actualHash.isBlank()) {
                return new LedgerCheck(
                        IntegrityStatus.DISCREPANCY_FOUND,
                        "Blockchain record " + recordId + " has no payload hash.",
                        false
                );
            }
            if (!actualHash.equalsIgnoreCase(expectedHash)) {
                return new LedgerCheck(
                        IntegrityStatus.DISCREPANCY_FOUND,
                        "Current database data does not match blockchain record " + recordId + ".",
                        false
                );
            }
            return new LedgerCheck(IntegrityStatus.VERIFIED, null, false);
        } catch (Exception exception) {
            return new LedgerCheck(
                    IntegrityStatus.NOT_CHECKED,
                    "Could not verify blockchain record " + recordId + ": " + exception.getMessage(),
                    false
            );
        }
    }

    private record LedgerCheck(
            IntegrityStatus status,
            String message,
            boolean missingRecord
    ) {}

    private IntegrityReport getIntegrityReport(UUID reportId) {
        return integrityReportRepo.findById(reportId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Integrity report not found."
                ));
    }

    private IntegrityReportResponse mapToIntegrityReportResponse(
            IntegrityReport report
    ) {
        return new IntegrityReportResponse(
                report.getId(),
                report.getTender().getId(),
                report.getTender().getTitle(),
                report.getBid() != null
                        ? report.getBid().getId()
                        : null,
                report.getAssignedAuditor() != null
                        ? report.getAssignedAuditor().getFullName()
                        : null,
                report.getType(),
                report.getSource(),
                report.getDescription(),
                report.getEvidenceReference(),
                report.getStatus(),
                report.getResolutionNotes(),
                report.getCreatedAt(),
                report.getUpdatedAt(),
                report.getResolvedAt()
        );
    }
    //endregion
}
