package icu.telepathystudios.puretender.service.audit;

import icu.telepathystudios.puretender.dto.audit.IntegrityReportResponse;
import icu.telepathystudios.puretender.model.classes.IntegrityReport;
import icu.telepathystudios.puretender.model.classes.Tender;
import icu.telepathystudios.puretender.model.classes.User;
import icu.telepathystudios.puretender.model.enums.*;
import icu.telepathystudios.puretender.repo.AuthRepo;
import icu.telepathystudios.puretender.repo.IntegrityReportRepo;
import icu.telepathystudios.puretender.repo.admin.TenderEvaluatorRepo;
import icu.telepathystudios.puretender.repo.bid.BidDocumentRepo;
import icu.telepathystudios.puretender.repo.bid.BidEvaluationRepo;
import icu.telepathystudios.puretender.repo.bid.BidRepo;
import icu.telepathystudios.puretender.repo.tender.TenderAwardRepo;
import icu.telepathystudios.puretender.repo.tender.TenderRepo;
import icu.telepathystudios.puretender.service.blockchain.BlockchainRecordService;
import icu.telepathystudios.puretender.service.blockchain.DocumentHashService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class EvaluationAuditServiceTest {

    @Mock AuthRepo authRepo;
    @Mock TenderRepo tenderRepo;
    @Mock TenderEvaluatorRepo tenderEvaluatorRepo;
    @Mock BidRepo bidRepo;
    @Mock BidDocumentRepo bidDocumentRepo;
    @Mock BidEvaluationRepo bidEvaluationRepo;
    @Mock TenderAwardRepo tenderAwardRepo;
    @Mock DocumentHashService documentHashService;
    @Mock IntegrityReportRepo integrityReportRepo;
    @Mock BlockchainRecordService blockchainRecordService;
    @Mock IntegrityReportService integrityReportService;

    private EvaluatorService evaluatorService;
    private AuditorService auditorService;
    private Authentication authentication;
    private User evaluator;
    private User auditor;
    private Tender tender;

    @BeforeEach
    void setUp() {
        evaluatorService = new EvaluatorService(authRepo, tenderRepo, tenderEvaluatorRepo, bidRepo,
                bidDocumentRepo, bidEvaluationRepo, tenderAwardRepo, documentHashService);
        auditorService = new AuditorService(authRepo, integrityReportRepo, tenderAwardRepo, tenderRepo,
                bidRepo, bidEvaluationRepo, bidDocumentRepo, documentHashService,
                blockchainRecordService, integrityReportService);
        authentication = mock(Authentication.class);
        evaluator = user(Role.EVALUATOR, AccountStatus.VERIFIED);
        auditor = user(Role.AUDITOR, AccountStatus.VERIFIED);
        tender = tender(TenderStatus.PUBLISHED);
    }

    @Test
    void openBidsOpensSubmittedBidsAfterOpeningDate() {
        prepareEvaluator();
        tender.setOpeningDate(Instant.now().minusSeconds(60));
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        when(tenderEvaluatorRepo.existsByTender_IdAndEvaluator_Id(tender.getId(), evaluator.getId())).thenReturn(true);
        var bid = new icu.telepathystudios.puretender.model.classes.Bid();
        bid.setStatus(BidStatus.SUBMITTED);
        when(bidRepo.findAllByTender_IdAndStatus(tender.getId(), BidStatus.SUBMITTED)).thenReturn(List.of(bid));

        var response = evaluatorService.openBids(tender.getId(), authentication);

        assertEquals(1, response.openedBidCount());
        assertEquals(BidStatus.OPENED, bid.getStatus());
        assertEquals(TenderStatus.UNDER_EVALUATION, tender.getStatus());
        verify(bidRepo).saveAll(List.of(bid));
    }

    @Test
    void openBidsRejectsTenderThatIsNotPublished() {
        prepareEvaluator();
        tender.setStatus(TenderStatus.SUBMITTED);
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        when(tenderEvaluatorRepo.existsByTender_IdAndEvaluator_Id(tender.getId(), evaluator.getId())).thenReturn(true);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> evaluatorService.openBids(tender.getId(), authentication));

        assertEquals(HttpStatus.CONFLICT.value(), exception.getStatusCode().value());
    }

    @Test
    void openBidsRejectsBeforeOpeningTime() {
        prepareEvaluator();
        tender.setOpeningDate(Instant.now().plusSeconds(600));
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        when(tenderEvaluatorRepo.existsByTender_IdAndEvaluator_Id(tender.getId(), evaluator.getId())).thenReturn(true);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> evaluatorService.openBids(tender.getId(), authentication));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
    }

    @Test
    void openBidsRejectsWhenThereAreNoSubmittedBids() {
        prepareEvaluator();
        tender.setOpeningDate(Instant.now().minusSeconds(60));
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        when(tenderEvaluatorRepo.existsByTender_IdAndEvaluator_Id(tender.getId(), evaluator.getId())).thenReturn(true);
        when(bidRepo.findAllByTender_IdAndStatus(tender.getId(), BidStatus.SUBMITTED)).thenReturn(List.of());

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> evaluatorService.openBids(tender.getId(), authentication));

        assertEquals(HttpStatus.CONFLICT.value(), exception.getStatusCode().value());
    }

    @Test
    void openBidsRequiresTenderAssignment() {
        prepareEvaluator();
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));
        when(tenderEvaluatorRepo.existsByTender_IdAndEvaluator_Id(tender.getId(), evaluator.getId())).thenReturn(false);

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> evaluatorService.openBids(tender.getId(), authentication));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
    }

    @Test
    void openBidsRejectsUnverifiedEvaluator() {
        evaluator.setStatus(AccountStatus.PENDING);
        when(authentication.getName()).thenReturn(evaluator.getEmail());
        when(authRepo.findByEmail(evaluator.getEmail())).thenReturn(Optional.of(evaluator));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> evaluatorService.openBids(tender.getId(), authentication));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
    }

    @Test
    void claimReportAssignsAuditorAndMovesReportUnderReview() {
        prepareAuditor();
        IntegrityReport report = report(IntegrityReportStatus.OPEN, tender);
        when(integrityReportRepo.findById(report.getId())).thenReturn(Optional.of(report));
        when(integrityReportRepo.save(report)).thenReturn(report);

        IntegrityReportResponse response = auditorService.claimReport(report.getId(), authentication);

        assertEquals(IntegrityReportStatus.UNDER_REVIEW, response.status());
        assertEquals(auditor, report.getAssignedAuditor());
    }

    @Test
    void claimReportRejectsAlreadyAssignedReport() {
        prepareAuditor();
        IntegrityReport report = report(IntegrityReportStatus.OPEN, tender);
        report.setAssignedAuditor(user(Role.AUDITOR, AccountStatus.VERIFIED));
        when(integrityReportRepo.findById(report.getId())).thenReturn(Optional.of(report));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> auditorService.claimReport(report.getId(), authentication));

        assertEquals(HttpStatus.CONFLICT.value(), exception.getStatusCode().value());
    }

    @Test
    void claimReportRejectsReportThatIsNotOpen() {
        prepareAuditor();
        IntegrityReport report = report(IntegrityReportStatus.RESOLVED, tender);
        when(integrityReportRepo.findById(report.getId())).thenReturn(Optional.of(report));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> auditorService.claimReport(report.getId(), authentication));

        assertEquals(HttpStatus.CONFLICT.value(), exception.getStatusCode().value());
    }

    @Test
    void auditTenderRejectsTenderOutsideAuditableStatuses() {
        prepareAuditor();
        tender.setStatus(TenderStatus.SUBMITTED);
        when(tenderRepo.findById(tender.getId())).thenReturn(Optional.of(tender));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> auditorService.auditTender(tender.getId(), authentication));

        assertEquals(HttpStatus.FORBIDDEN.value(), exception.getStatusCode().value());
        verifyNoInteractions(blockchainRecordService);
    }

    private void prepareEvaluator() {
        when(authentication.getName()).thenReturn(evaluator.getEmail());
        when(authRepo.findByEmail(evaluator.getEmail())).thenReturn(Optional.of(evaluator));
    }

    private void prepareAuditor() {
        when(authentication.getName()).thenReturn(auditor.getEmail());
        when(authRepo.findByEmail(auditor.getEmail())).thenReturn(Optional.of(auditor));
    }

    private static IntegrityReport report(IntegrityReportStatus status, Tender tender) {
        IntegrityReport report = new IntegrityReport();
        report.setId(UUID.randomUUID());
        report.setTender(tender);
        report.setType(IntegrityReportType.HASH_MISMATCH);
        report.setSource(IntegrityReportSource.SYSTEM_VERIFICATION);
        report.setDescription("Hash mismatch");
        report.setStatus(status);
        return report;
    }

    private static User user(Role role, AccountStatus status) {
        User user = new User();
        user.setId(UUID.randomUUID());
        user.setFullName(role.name() + " Person");
        user.setEmail(role.name().toLowerCase() + "@example.com");
        user.setRole(role);
        user.setStatus(status);
        return user;
    }

    private static Tender tender(TenderStatus status) {
        Tender tender = new Tender();
        tender.setId(UUID.randomUUID());
        tender.setTitle("Road Works");
        tender.setDescription("Repair roads");
        tender.setEstimatedValue(new BigDecimal("1000.00"));
        tender.setSubmissionDeadline(Instant.now().plusSeconds(3600));
        tender.setOpeningDate(Instant.now().minusSeconds(60));
        tender.setStatus(status);
        tender.setAuthority(user(Role.AUTHORITY, AccountStatus.VERIFIED));
        return tender;
    }
}
