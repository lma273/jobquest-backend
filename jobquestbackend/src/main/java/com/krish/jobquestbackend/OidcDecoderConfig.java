package com.krish.jobquestbackend;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.*;

@Configuration
public class OidcDecoderConfig {

    @Value("${auth0.issuer}")
    private String issuer;

    @Value("${auth0.jwks-uri}")
    private String jwksUri;

    // ✳️ Bản tối giản: chỉ verify chữ ký + issuer để cô lập lỗi
    @Bean
    public JwtDecoder idTokenDecoder() {
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withJwkSetUri(jwksUri).build();

        // Validate issuer + iat/exp
        OAuth2TokenValidator<Jwt> withIssuer = JwtValidators.createDefaultWithIssuer(issuer);

        decoder.setJwtValidator(withIssuer);
        return decoder;
    }
}
