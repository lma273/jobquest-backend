package com.krish.jobquestbackend;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class CandidateService {
    @Autowired
    CandidateRepository candidateRepository;

    @Autowired
    PasswordEncoder passwordEncoder;

    public List<Candidate> allCandidates() {
        return candidateRepository.findAll();
    }

    public Optional<Candidate> singleCandidate(String email) {
        return candidateRepository.findByEmail(email);
    }

    public Candidate createCandidate(Candidate candidate) {
        String hashedPassword = passwordEncoder.encode(candidate.getPassword());
        candidate.setPassword(hashedPassword);
        return candidateRepository.insert(candidate);
    }

    // Tìm theo email
    public Optional<Candidate> findByEmail(String email) {
        return candidateRepository.findByEmail(email);
    }

    // Tìm theo auth0Sub
    public Optional<Candidate> findByAuth0Sub(String sub) {
        return candidateRepository.findByAuth0Sub(sub);
    }

    // Link SSO
    public Candidate linkAuth0(Candidate u, String sub, boolean remember) {
        u.setAuth0Sub(sub);
        if (remember) u.setSsoPreferred(true);
        if (u.getAuthProvider() == null) u.setAuthProvider("local");
        return candidateRepository.save(u); // ✅ LƯU DB
    }

    // Unlink
    public void unlinkAuth0(Candidate u) {
        u.setAuth0Sub(null);
        u.setSsoPreferred(false);
        candidateRepository.save(u); // ✅ LƯU DB
    }

    // Đổi last login provider
    public void updateLastLoginProvider(Candidate u, String provider) {
        u.setLastLoginProvider(provider);
        candidateRepository.save(u); // ✅ LƯU DB
    }

//    // Tạo “shadow user” từ SSO (khi chưa tồn tại)
//    public Candidate createShadowUserFromSSO(String email, String sub) {
//        Candidate u = new Candidate();
//        u.setEmail(email);
//        u.setName(email != null ? email : "SSO User");
//        u.setAuthProvider("auth0");
//        u.setAuth0Sub(sub);
//        u.setSsoPreferred(true);
//        // TODO: repo.save(u)
//        return u;
//    }

}
