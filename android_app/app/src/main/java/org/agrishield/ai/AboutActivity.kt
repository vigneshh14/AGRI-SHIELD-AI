package org.agrishield.ai

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import org.agrishield.ai.databinding.ActivityAboutBinding

class AboutActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val b = ActivityAboutBinding.inflate(layoutInflater)
        setContentView(b.root)
        b.btnBack.setOnClickListener { finish() }
    }
}
