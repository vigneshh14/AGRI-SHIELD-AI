plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "org.agrishield.ai"
    compileSdk = 34

    defaultConfig {
        applicationId = "org.agrishield.ai"
        minSdk = 28
        targetSdk = 34          // the test device runs Android 14 (API 34)
        versionCode = 1
        versionName = "0.1.0-phase4"

        // The Infinix NOTE 30 5G is arm64-v8a. The ExecuTorch AAR also ships
        // x86_64; excluding it roughly halves the APK. Add x86_64 back only if
        // you need to run on an emulator.
        ndk { abiFilters += listOf("arm64-v8a") }

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug { isMinifyEnabled = false }
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"),
                          "proguard-rules.pro")
        }
    }

    // The .pte is already compressed data; letting aapt re-compress it only
    // slows the install and gains nothing.
    androidResources { noCompress += "pte" }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { viewBinding = true }
}

dependencies {
    // ExecuTorch Android runtime, XNNPACK backend. Version deliberately pinned
    // to 1.5.1 to match the version the .pte was exported with.
    implementation("org.pytorch:executorch-android:1.5.1")

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.exifinterface:exifinterface:1.3.7")

    // Lifecycle-aware coroutines for ResultViewModel / ResultActivity /
    // PreviewActivity (viewModelScope, lifecycleScope, repeatOnLifecycle).
    // All three already arrive transitively via activity-ktx; they are declared
    // because the app calls them directly. Versions chosen not to force an
    // upgrade past what activity-ktx 1.9.3 resolves, and built with a Kotlin
    // version the 1.9.24 compiler can read.
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.6.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.6.2")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:rules:1.6.1")
}
