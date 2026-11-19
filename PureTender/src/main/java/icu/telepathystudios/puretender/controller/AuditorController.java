package icu.telepathystudios.puretender.controller;

import icu.telepathystudios.puretender.dto.audit.IntegrityReportResponse;
import icu.telepathystudios.puretender.dto.audit.ResolveIntegrityReportRequest;
import icu.telepathystudios.puretender.dto.audit.AwardHeldTenderRequest;
import icu.telepathystudios.puretender.dto.audit.AuditorTenderAuditResponse;
import icu.telepathystudios.puretender.dto.audit.AuditorTenderSummaryResponse;
import icu.telepathystudios.puretender.dto.bid.BidProposalDownload;
import icu.telepathystudios.puretender.dto.tender.TenderAwardResponse;
import icu.telepathystudios.puretender.service.audit.AuditorService;
import jakarta.validation.Valid;

import lombok.RequiredArgsConstructor;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;
import java.util.List;

@RestController
@RequestMapping("/api/v1/auditor")
@RequiredArgsConstructor
@PreAuthorize("hasRole('AUDITOR')")
public class AuditorController {

    private final AuditorService auditorService;

    @GetMapping("/tenders/review-queue")
    public ResponseEntity<Page<AuditorTenderSummaryResponse>> getReviewQueue(
            Authentication authentication,
            @PageableDefault(size = 10) Pageable pageable
    ) {
        return ResponseEntity.ok(auditorService.getReviewQueue(authentication, pageable));
    }

    @GetMapping("/tenders/flagged")
    public ResponseEntity<Page<AuditorTenderSummaryResponse>> getFlaggedTenders(
            Authentication authentication,
            @PageableDefault(size = 10) Pageable pageable
    ) {
        return ResponseEntity.ok(auditorService.getFlaggedTenders(authentication, pageable));
    }

    @GetMapping("/tenders/completed")
    public ResponseEntity<Page<AuditorTenderSummaryResponse>> getCompletedTenders(
            Authentication authentication,
            @PageableDefault(size = 10) Pageable pageable
    ) {
        return ResponseEntity.ok(auditorService.getCompletedTenders(authentication, pageable));
    }

    @PostMapping("/tenders/{tenderId}/audit")
    public ResponseEntity<AuditorTenderAuditResponse> auditTender(
            @PathVariable UUID tenderId,
            Authentication authentication
    ) {
        return ResponseEntity.ok(auditorService.auditTender(tenderId, authentication));
    }

    @PostMapping("/tenders/{tenderId}/integrity-check")
    public ResponseEntity<AuditorTenderAuditResponse> checkTenderIntegrity(
            @PathVariable UUID tenderId,
            Authentication authentication
    ) {
        return ResponseEntity.ok(auditorService.auditTender(tenderId, authentication));
    }

    @GetMapping("/bids/{bidId}/proposal")
    public ResponseEntity<byte[]> downloadProposal(
            @PathVariable UUID bidId,
            Authentication authentication
    ) {
        BidProposalDownload proposal = auditorService.downloadProposal(bidId, authentication);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType(proposal.contentType()));
        headers.setContentDisposition(ContentDisposition.attachment()
                .filename(proposal.fileName()).build());
        headers.setContentLength(proposal.fileData().length);
        return new ResponseEntity<>(proposal.fileData(), headers, HttpStatus.OK);
    }

    // 1. View all integrity reports
    @GetMapping("/reports")
    public ResponseEntity<Page<IntegrityReportResponse>> getReports(
            Authentication authentication,
            @PageableDefault(size = 10) Pageable pageable
    ) {
        return ResponseEntity.ok(
                auditorService.getReports(authentication, pageable)
        );
    }

    // 2. View an individual report
    @GetMapping("/reports/{reportId}")
    public ResponseEntity<IntegrityReportResponse> getReport(
            @PathVariable UUID reportId,
            Authentication authentication
    ) {
        return ResponseEntity.ok(
                auditorService.getReport(reportId, authentication)
        );
    }

    // 3. Claim an open report
    @PostMapping("/reports/{reportId}/claim")
    public ResponseEntity<IntegrityReportResponse> claimReport(
            @PathVariable UUID reportId,
            Authentication authentication
    ) {
        return ResponseEntity.ok(
                auditorService.claimReport(reportId, authentication)
        );
    }

    // 4. Submit investigation findings
    @PostMapping("/reports/{reportId}/resolve")
    public ResponseEntity<IntegrityReportResponse> resolveReport(
            @PathVariable UUID reportId,
            @Valid @RequestBody ResolveIntegrityReportRequest request,
            Authentication authentication
    ) {
        return ResponseEntity.ok(
                auditorService.resolveReport(
                        reportId,
                        request,
                        authentication
                )
        );
    }

    @PostMapping("/tenders/{tenderId}/award")
    public ResponseEntity<TenderAwardResponse> awardHeldTender(
            @PathVariable UUID tenderId,
            @Valid @RequestBody AwardHeldTenderRequest request,
            Authentication authentication
    ) {
        return ResponseEntity.ok(
                auditorService.awardHeldTender(tenderId, request, authentication)
        );
    }
}
