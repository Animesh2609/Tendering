package icu.telepathystudios.puretender.repo.tender;

import icu.telepathystudios.puretender.model.classes.TenderAward;
import icu.telepathystudios.puretender.model.enums.TenderStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface TenderAwardRepo
        extends JpaRepository<TenderAward, UUID> {

    Optional<TenderAward> findByTender_Id(UUID tenderId);

    Page<TenderAward> findAllByTender_Status(TenderStatus status, Pageable pageable);

    boolean existsByTender_Id(UUID tenderId);
}
