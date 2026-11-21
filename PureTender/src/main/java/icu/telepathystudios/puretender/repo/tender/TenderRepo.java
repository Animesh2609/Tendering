package icu.telepathystudios.puretender.repo.tender;

import icu.telepathystudios.puretender.model.classes.Tender;
import icu.telepathystudios.puretender.model.enums.TenderStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.Instant;
import java.util.List;
import java.util.Collection;
import java.util.Optional;
import java.util.UUID;

public interface TenderRepo extends JpaRepository<Tender, UUID>
{
    Page<Tender> findAllByAuthority_Id(
            UUID authorityId,
            Pageable pageable
    );

    Page<Tender> findAllByStatus(
            TenderStatus status,
            Pageable pageable
    );

    Page<Tender> findAllByStatusIn(
            Collection<TenderStatus> statuses,
            Pageable pageable
    );

    Optional<Tender> findByIdAndAuthority_Id(
            UUID tenderId,
            UUID authorityId
    );

    Page<Tender> findAllByStatusOrderByCreatedAtDesc(
            TenderStatus status,
            Pageable pageable
    );

    Page<Tender> findAllByStatusOrderByPublishedAtDesc(
            TenderStatus status,
            Pageable pageable
    );

    List<Tender> findAllByStatusAndSubmissionDeadlineLessThanEqual(
            TenderStatus status,
            Instant deadline
    );
}
