package com.krish.jobquestbackend;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;

@Configuration
public class Auth0TokenVerifier {

    @Bean
    JwtDecoder auth0IdTokenDecoder(@Value("${auth0.issuer}") String issuer) {
        return NimbusJwtDecoder.withJwkSetUri(issuer + ".well-known/jwks.json").build();
    }
}