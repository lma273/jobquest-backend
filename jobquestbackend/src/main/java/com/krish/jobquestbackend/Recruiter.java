package com.krish.jobquestbackend;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.bson.types.ObjectId;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Document(collection = "recruiters")
@Data
@AllArgsConstructor
@NoArgsConstructor
public class Recruiter {
    @Id
    private ObjectId id;
    private String name;
    private String email;
    private String password;
    private String company;
    private String location;
    private List<ObjectId> jobIds;

    private String authProvider;       // "local" | "auth0"
    private String auth0Sub;           // nullable, unique (DB index sparse)
    private Boolean ssoPreferred;      // default false
    private String lastLoginProvider;  // "local" | "auth0"


    public Recruiter(String name, String email, String password, String company, String location, List<ObjectId> jobIds) {
        this.name = name;
        this.email = email;
        this.password = password;
        this.company = company;
        this.location = location;
        this.jobIds = jobIds;
    }
    public Recruiter(String name, String email, String password, String company, String location) {
        this.name = name;
        this.email = email;
        this.password = password;
        this.company = company;
        this.location = location;
        this.jobIds = new ArrayList<>(); // 👈 tránh null
    }


    public String getEmail() {
        return email;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public String getAuthProvider() {
        return authProvider;
    }

    public void setAuthProvider(String authProvider) {
        this.authProvider = authProvider;
    }

    public String getAuth0Sub() {
        return auth0Sub;
    }

    public void setAuth0Sub(String auth0Sub) {
        this.auth0Sub = auth0Sub;
    }

    public Boolean getSsoPreferred() {
        return ssoPreferred;
    }

    public void setSsoPreferred(Boolean ssoPreferred) {
        this.ssoPreferred = ssoPreferred;
    }

    public String getLastLoginProvider() {
        return lastLoginProvider;
    }

    public void setLastLoginProvider(String lastLoginProvider) {
        this.lastLoginProvider = lastLoginProvider;
    }

    @JsonProperty("id")
    public String getIdString() {
        return id != null ? id.toHexString() : null;
    }

    @JsonProperty("jobIds")
    public List<String> getJobIdsString() {
        if (jobIds != null) {
            return jobIds.stream().map(ObjectId::toHexString).collect(Collectors.toList());
        } else {
            return null;
        }
    }

    public void addJobId(ObjectId jobId) {
        if (this.jobIds == null) {
            this.jobIds = new ArrayList<>();
        }
        this.jobIds.add(jobId);
    }

    public void removeJobId(ObjectId jobId) {
        if (this.jobIds != null) {
            this.jobIds.remove(jobId);
        }
    }
}
