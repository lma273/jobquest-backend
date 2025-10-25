package com.krish.jobquestbackend;

import org.bson.types.ObjectId;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RecruiterRepository extends MongoRepository<Recruiter, ObjectId> {
    Optional<Recruiter> findByEmail(String email);
    Optional<Recruiter> findByAuth0Sub(String auth0Sub);
}
