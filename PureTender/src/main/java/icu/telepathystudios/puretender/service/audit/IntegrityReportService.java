package icu.telepathystudios.puretender.service.audit;

import icu.telepathystudios.puretender.model.classes.Bid;
import icu.telepathystudios.puretender.model.classes.IntegrityReport;
import icu.telepathystudios.puretender.model.classes.Tender;
import icu.telepathystudios.puretender.model.enums.*;
import icu.telepathystudios.puretender.repo.*;

import icu.telepathystudios.puretender.repo.bid.BidRepo;
import icu.telepathystudios.puretender.repo.tender.TenderRepo;
import lombok.RequiredArgsConstructor;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.UUID;
import java.util.List;

@Service
@RequiredArgsConstructor
public class IntegrityReportService {

    private final TenderRepo tenderRepo;
    private final BidRepo bidRepo;
    private final IntegrityReportRepo integrityReportRepo;

    //region System integrity report creation
    // Called internally when system/blockchain verification finds a discrepancy.
    @Transactional
    public IntegrityReport createSystemReport(
            UUID tenderId,
            UUID bidId,
            IntegrityReportType type,
            String description,
            String evidenceReference
    ) {

        Tender tender = tenderRepo.findById(tenderId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Tender not found."
                ));

        if (tender.getStatus() != TenderStatus.UNDER_EVALUATION
                && tender.getStatus() != TenderStatus.ON_HOLD
                && tender.getStatus() != TenderStatus.AWARDED) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "Integrity reports require a tender under evaluation, on hold, or awarded."
            );
        }

        Bid bid = null;

        if (bidId != null) {
            bid = bidRepo.findById(bidId)
                    .orElseThrow(() -> new ResponseStatusException(
                            HttpStatus.NOT_FOUND,
                            "Bid not found."
                    ));

            if (!bid.getTender().getId().equals(tenderId)) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "The specified bid does not belong to this tender."
                );
            }
        }

        List<IntegrityReportStatus> activeStatuses = List.of(
                IntegrityReportStatus.OPEN,
                IntegrityReportStatus.UNDER_REVIEW
        );
        var existingReport = integrityReportRepo
                .findFirstByTender_IdAndBid_IdAndTypeAndStatusIn(
                        tenderId, bidId, type, activeStatuses
                );
        if (existingReport.isPresent()) {
            return existingReport.get();
        }

        IntegrityReport report = new IntegrityReport();

        report.setTender(tender);
        report.setBid(bid);
        report.setType(type);
        report.setSource(IntegrityReportSource.BLOCKCHAIN_VERIFICATION);
        report.setDescription(description);
        report.setEvidenceReference(evidenceReference);
        report.setStatus(IntegrityReportStatus.OPEN);

        IntegrityReport savedReport = integrityReportRepo.save(report);
        if (tender.getStatus() != TenderStatus.ON_HOLD) {
            tender.setStatus(TenderStatus.ON_HOLD);
            tenderRepo.save(tender);
        }

        return savedReport;
    }
    //endregion
}
