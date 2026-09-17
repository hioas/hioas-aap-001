package com.hioas.aap;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class ToolchainSmokeTest {

    @Test
    void jdkIs25() {
        assertThat(Runtime.version().feature()).isEqualTo(25);
    }
}
